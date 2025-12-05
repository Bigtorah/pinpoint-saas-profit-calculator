import streamlit as st
import os
import requests
import json
import time
import base64

# --- PINPOINT BRAND COLORS ---
PP_BLUE_DARK = "#0F4C81" 
PP_BLUE_LIGHT = "#1A73E8"
PP_ACCENT_PURPLE = "#8E44AD"
PP_BG_WHITE = "#ffffff"

# --- API Configuration ---
# The API key is injected by the environment. Leave this as an empty string.
API_KEY = ""
MODEL_NAME = "gemini-2.5-flash-preview-09-2025"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

# --- CALCULATION CONSTANTS (Based on the previous app) ---
DUAL_PROFIT_PCT = 0.015       # 1.5% profit for Dual Pricing
FLAT_PROFIT_PCT = 0.01        # 1.0% profit for Flat Rate
REVSHARE = 0.50               # 50% to agent
ACCOUNT_ON_FILE = 7.50
GATEWAY = 10.00
PER_TERMINAL_FIRST = 4.00
PER_TERMINAL_ADDITIONAL = 2.00
MOBILE_MONTHLY = 10.00
P8_TERMINAL = 310.00
P12_TERMINAL = 166.75
STAND_P8 = 35.00
MOBILE_APP_DOWNLOAD = 30.00
DUAL_COMPLIANCE = 3.00

# --- TERMINAL CHOICES FOR PROPOSAL ---
TERMINAL_OPTIONS = {
    "Dejavoo P8": P8_TERMINAL,
    "Dejavoo P12 Mini": P12_TERMINAL,
    "Pax A920 (Premium)": 450.00
}

# --- JSON SCHEMA for AI Extraction ---
# We use a structured output to ensure the AI returns data reliably
SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "monthly_volume": {"type": "NUMBER", "description": "The merchant's total monthly processing volume in US dollars."},
        "monthly_fees": {"type": "NUMBER", "description": "The total monthly fixed fees currently paid by the merchant."},
        "current_rate_percentage": {"type": "NUMBER", "description": "The merchant's current blended effective processing rate as a decimal (e.g., 0.025 for 2.5%)."},
        "current_terminal_count": {"type": "INTEGER", "description": "The number of terminals/devices the merchant currently uses (estimate)."}
    },
    "required": ["monthly_volume", "monthly_fees", "current_rate_percentage", "current_terminal_count"]
}


# --------------------------------------------------------------------------------
#                               AI EXTRACTION FUNCTIONS
# --------------------------------------------------------------------------------

def encode_image(uploaded_file):
    """Encodes the uploaded file to base64 for API transmission."""
    return base64.b64encode(uploaded_file.getvalue()).decode("utf-8")

def call_gemini_api(base64_image):
    """Calls the Gemini API to analyze the image and extract structured data."""
    system_prompt = (
        "You are a hyper-accurate financial data extraction specialist for Pinpoint Payments. "
        "Analyze the provided credit card processing statement image. Extract the four required "
        "fields (monthly_volume, monthly_fees, current_rate_percentage, current_terminal_count) "
        "and provide the output ONLY as a JSON object conforming to the provided schema. "
        "If a specific value is missing, make a reasonable estimate based on typical processing statements."
    )
    
    # Construct the payload for the API call
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": "Analyze this credit card processing statement and return the data as JSON."},
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",  # Assuming statements are usually JPG/PDF converted to JPG
                            "data": base64_image
                        }
                    }
                ]
            }
        ],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": SCHEMA
        }
    }

    # Implement exponential backoff for robustness
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = requests.post(API_URL, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
            response.raise_for_status() # Raises an HTTPError if the status is 4xx or 5xx
            
            result = response.json()
            
            # Check for candidates and content part text
            if (result.get('candidates') and 
                result['candidates'][0].get('content') and 
                result['candidates'][0]['content'].get('parts') and 
                result['candidates'][0]['content']['parts'][0].get('text')):
                
                # The response text is a JSON string
                json_string = result['candidates'][0]['content']['parts'][0]['text']
                return json.loads(json_string)

            else:
                st.error("AI analysis failed to return valid content structure.")
                return None

        except requests.exceptions.HTTPError as e:
            st.error(f"HTTP Error during API call (Attempt {attempt+1}): {e}")
            if attempt < max_retries - 1 and e.response.status_code in [429, 500, 503]:
                # Exponential backoff: 2^attempt seconds
                time.sleep(2 ** attempt)
            else:
                return None
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            return None
    return None


# --------------------------------------------------------------------------------
#                               CALCULATION LOGIC
# --------------------------------------------------------------------------------

def calculate_proposal_fees(base_data, terminal, num_terminals):
    """Calculates Pinpoint's proposed costs and profit."""
    
    # 1. Calculate Monthly Fees (as per previous app's constants)
    monthly_first_terminal = PER_TERMINAL_FIRST
    monthly_additional_terminals = max(num_terminals - 1, 0) * PER_TERMINAL_ADDITIONAL
    
    # Simple Terminal Price Lookup
    one_time_terminal = TERMINAL_OPTIONS.get(terminal, 0.0) 

    monthly_fees_total = (
        ACCOUNT_ON_FILE
        + GATEWAY
        + monthly_first_terminal
        + monthly_additional_terminals
    )
    
    # 2. Calculate Pricing Profits
    dual_gross = base_data["monthly_volume"] * DUAL_PROFIT_PCT
    flat_gross = base_data["monthly_volume"] * FLAT_PROFIT_PCT

    # 3. Compile Results
    results = {
        # Current Costs (from AI analysis)
        "current_monthly_cost": base_data["monthly_volume"] * base_data["current_rate_percentage"] + base_data["monthly_fees"],
        "current_volume": base_data["monthly_volume"],
        
        # Dual Pricing Proposal (Merchant always pays 3.99% flat, covers fees)
        "dual_proposed_monthly": base_data["monthly_volume"] * 0.0399 + DUAL_COMPLIANCE, # Example rate of 3.99%
        "dual_agent_profit_monthly": dual_gross * REVSHARE,
        "dual_one_time": one_time_terminal + DUAL_COMPLIANCE,

        # Flat Rate Proposal (Custom negotiated rate, includes fees)
        "flat_proposed_monthly": base_data["monthly_volume"] * 0.0295 + (base_data["monthly_volume"] / 1000) * 0.30 + monthly_fees_total, # Example flat rate
        "flat_agent_profit_monthly": flat_gross * REVSHARE,
        "flat_one_time": one_time_terminal,
        
        # Monthly fees to compare against savings
        "pinpoint_monthly_fees": monthly_fees_total
    }
    return results


# --------------------------------------------------------------------------------
#                               STREAMLIT UI
# --------------------------------------------------------------------------------

st.set_page_config(
    page_title="Pinpoint – Statement Analyzer & Proposal Generator",
    page_icon="🔎",
    layout="wide",
)

st.markdown(
    f"""
    <style>
    .main {{ background-color: {PP_BG_WHITE}; padding: 2rem; }}
    h1, h2, h3, h4 {{ color: {PP_BLUE_DARK}; font-weight: 700; letter-spacing: -0.02em; padding-top: 10px; }}
    .pp-subtitle {{ color: #4A4F5A; font-size: 1.05rem; margin-bottom: 2rem; text-align: center; max-width: 700px; margin-left: auto; margin-right: auto; line-height: 1.5; }}
    .stFileUploader label p {{ color: {PP_ACCENT_PURPLE}; font-weight: 600; font-size: 1.1rem; }}
    .stButton>button {{ background-color: {PP_BLUE_DARK}; color: white; border-radius: 20px; padding: 0.5rem 1.5rem; border: none; font-weight: 600; transition: background-color 0.3s; }}
    .stButton>button:hover {{ background-color: {PP_BLUE_LIGHT}; color: white; }}
    .data-summary-box {{ border: 2px solid {PP_ACCENT_PURPLE}; border-radius: 12px; padding: 15px; margin-bottom: 20px; background-color: #f7f3f9;}}
    .proposal-card {{ border: 1px solid #E0E0E0; border-radius: 12px; padding: 20px; margin-top: 20px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); min-height: 450px;}}
    .dual-pricing-card {{ border: 2px solid {PP_ACCENT_PURPLE}; }}
    .metric-value {{ font-size: 1.8rem; font-weight: 800; color: {PP_BLUE_DARK}; }}
    hr {{ border-top: 2px solid #EEEEEE; margin: 2rem 0; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Header ---
st.markdown(
    f"<h2 style='text-align:center; margin-bottom:0.10rem; color:{PP_BLUE_DARK};'>Statement Analyzer & Proposal Generator</h2>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p class='pp-subtitle'>Pinpoint exactly what clients are paying. Scan any statement to instantly generate a commission forecast and client savings proposal.</p>",
    unsafe_allow_html=True,
)
st.write("---")

# --- Statement Upload ---
st.markdown("### 📥 Step 1: Upload Client Statement")

uploaded_file = st.file_uploader(
    "Upload Image of Statement (JPG or PNG)", 
    type=["jpg", "jpeg", "png"]
)

if uploaded_file:
    st.image(uploaded_file, caption='Statement Preview', width=300)
    
    # Store the extracted data in session state to avoid re-running API call
    if 'extracted_data' not in st.session_state:
        st.session_state.extracted_data = None
        
    if st.button("Analyze Statement with AI"):
        st.session_state.extracted_data = None # Clear previous
        
        with st.spinner("AI is reading the statement..."):
            base64_image = encode_image(uploaded_file)
            extracted_data = call_gemini_api(base64_image)
            
            if extracted_data:
                st.session_state.extracted_data = extracted_data
                st.success("Analysis complete! Review the extracted data below.")
            else:
                st.session_state.extracted_data = "ERROR"
                st.error("AI analysis failed. Please review the image quality or manually enter data.")

# --- Manual Data Entry / AI Output ---
st.write("---")
st.markdown("### 📝 Step 2: Review & Finalize Data")

base_data_form = st.container()

# Initialize data structure
if st.session_state.get('extracted_data') == "ERROR":
    initial_volume = 0.0
    initial_fees = 0.0
    initial_rate = 0.0
    initial_count = 1
    st.warning("Please enter the values below manually.")
elif st.session_state.get('extracted_data'):
    data = st.session_state.extracted_data
    initial_volume = data.get('monthly_volume', 0.0)
    initial_fees = data.get('monthly_fees', 0.0)
    initial_rate = data.get('current_rate_percentage', 0.0)
    initial_count = data.get('current_terminal_count', 1)
    
    # Display AI Extracted Summary
    st.markdown(f'<div class="data-summary-box">', unsafe_allow_html=True)
    st.markdown(f"**AI Extracted Volume:** <span class='metric-value'>${initial_volume:,.0f}</span>", unsafe_allow_html=True)
    st.markdown(f"**AI Extracted Fees:** <span class='metric-value'>${initial_fees:,.2f}</span>", unsafe_allow_html=True)
    st.markdown(f"**AI Extracted Rate:** <span class='metric-value'>{(initial_rate * 100):.2f}%</span>", unsafe_allow_html=True)
    st.markdown(f'</div>', unsafe_allow_html=True)

else:
    initial_volume = 15000.0
    initial_fees = 75.00
    initial_rate = 0.028  # 2.8%
    initial_count = 1

# Manual Data Input Fields (Pre-populated by AI if successful)
with base_data_form:
    st.markdown("#### Input Merchant Financials")
    colV, colR, colF = st.columns(3)
    
    volume_input = colV.number_input(
        "Monthly Processing Volume ($)", 
        min_value=0.0, 
        value=initial_volume, 
        step=100.0
    )
    fees_input = colR.number_input(
        "Current Total Fixed Monthly Fees ($)", 
        min_value=0.0, 
        value=initial_fees, 
        step=5.0
    )
    rate_input = colF.number_input(
        "Current Blended Effective Rate (e.g., 0.025 for 2.5%)", 
        min_value=0.0, 
        max_value=1.0, 
        value=initial_rate, 
        format="%.4f"
    )
    
    st.markdown("#### Input Terminal Selection")
    colT, colN, colTerminal = st.columns(3)
    
    terminal_type = colT.selectbox(
        "Proposed Terminal Model",
        options=list(TERMINAL_OPTIONS.keys()),
        index=list(TERMINAL_OPTIONS.keys()).index("Dejavoo P8") if "Dejavoo P8" in TERMINAL_OPTIONS else 0
    )
    num_terminals = colN.number_input(
        "Number of Terminals Required", 
        min_value=1, 
        value=initial_count, 
        step=1
    )
    
    # Re-run calculation button
    if st.button("Generate Proposal"):
        # Save validated data to session state for calculation
        st.session_state.base_data = {
            "monthly_volume": volume_input,
            "monthly_fees": fees_input,
            "current_rate_percentage": rate_input,
            "current_terminal_count": num_terminals # Use selected count for consistency
        }
        st.session_state.terminal_choice = terminal_type
        st.session_state.num_terminals = num_terminals
        st.session_state.proposal_generated = True

# --- Proposal Results ---

if st.session_state.get('proposal_generated', False) and st.session_state.get('base_data'):
    st.write("---")
    st.markdown(f"### 🎯 Step 3: Pinpoint Payments Client Proposal")
    
    base_data = st.session_state.base_data
    terminal = st.session_state.terminal_choice
    num_terminals = st.session_state.num_terminals
    
    proposal = calculate_proposal_fees(base_data, terminal, num_terminals)

    # Calculate Savings
    current_annual_cost = proposal["current_monthly_cost"] * 12
    dual_annual_cost = proposal["dual_proposed_monthly"] * 12
    flat_annual_cost = proposal["flat_proposed_monthly"] * 12
    
    dual_savings = current_annual_cost - dual_annual_cost
    flat_savings = current_annual_cost - flat_annual_cost

    # Display Current Metrics
    st.markdown(f"#### Client Status (Total Annual Cost: ${current_annual_cost:,.2f})")
    colCurr1, colCurr2, colCurr3 = st.columns(3)
    colCurr1.metric("Current Monthly Volume", f"${base_data['monthly_volume']:,.0f}")
    colCurr2.metric("Current Effective Rate", f"{(base_data['current_rate_percentage'] * 100):.2f}%")
    colCurr3.metric("Current Monthly Cost", f"${proposal['current_monthly_cost']:,.2f}")
    
    st.write("---")
    
    # Display Proposal Comparison
    colDual, colFlat = st.columns(2)
    
    # Dual Pricing Card
    with colDual:
        st.markdown(f'<div class="proposal-card dual-pricing-card">', unsafe_allow_html=True)
        st.markdown(f"#### Dual Pricing Proposal (3.99%)")
        st.markdown(f"**Annual Savings:** <span style='color: green; font-size: 1.8rem; font-weight: 800;'>${dual_savings:,.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"**Agent Monthly Commission:** <span style='font-size: 1.2rem; color: {PP_BLUE_DARK}; font-weight: 700;'>${proposal['dual_agent_profit_monthly']:,.2f}</span>", unsafe_allow_html=True)
        
        st.markdown("##### Fees & Equipment")
        st.markdown(f"- Proposed Terminal: **{terminal}**")
        st.markdown(f"- Proposed Terminals Cost (One-Time): **${proposal['dual_one_time']:,.2f}**")
        st.markdown(f"- Total Monthly Cost to Client: **${proposal['dual_proposed_monthly']:,.2f}**")
        st.markdown('</div>', unsafe_allow_html=True)
        
    # Flat Rate Card
    with colFlat:
        st.markdown(f'<div class="proposal-card">', unsafe_allow_html=True)
        st.markdown(f"#### Flat Rate Proposal (2.95% + $0.30)")
        st.markdown(f"**Annual Savings:** <span style='color: green; font-size: 1.8rem; font-weight: 800;'>${flat_savings:,.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"**Agent Monthly Commission:** <span style='font-size: 1.2rem; color: {PP_BLUE_DARK}; font-weight: 700;'>${proposal['flat_agent_profit_monthly']:,.2f}</span>", unsafe_allow_html=True)
        
        st.markdown("##### Fees & Equipment")
        st.markdown(f"- Proposed Terminal: **{terminal}**")
        st.markdown(f"- Proposed Terminals Cost (One-Time): **${proposal['flat_one_time']:,.2f}**")
        st.markdown(f"- Total Monthly Cost to Client: **${proposal['flat_proposed_monthly']:,.2f}**")
        st.markdown('</div>', unsafe_allow_html=True)
        
    st.write("---")
    st.markdown(f"#### 📱 Terminal Recommendation")
    st.info(f"The proposal includes the **{terminal}** terminal, costing **${TERMINAL_OPTIONS.get(terminal, 0.0):,.2f}** one-time, which is a great modern solution for a merchant with ${base_data['monthly_volume']:,.0f} in volume.")
