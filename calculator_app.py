import streamlit as st
import os

# --- PINPOINT BRAND COLORS ---
# Primary Blue (Dark): Used for headings, strong accents, and button backgrounds
PP_BLUE_DARK = "#0F4C81" 
# Secondary Blue (Light): Used for borders, highlights, and secondary text
PP_BLUE_LIGHT = "#1A73E8"
# Accent Purple (for highlights/emphasis, mimicking the box in the hero image)
PP_ACCENT_PURPLE = "#8E44AD"
# Background: White
PP_BG_WHITE = "#ffffff"

# -----------------------------
#   PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="Pinpoint Payments – Agent Revenue & Fees Calculator",
    page_icon="💳",
    layout="wide",
)

# -----------------------------
#   BRAND STYLING (CSS Overhaul)
# -----------------------------
st.markdown(
    f"""
    <style>
    /* Global Styles */
    .main {{ 
        background-color: {PP_BG_WHITE}; 
        padding: 2rem;
    }}
    
    /* Typography */
    h1, h2, h3, h4 {{
        color: {PP_BLUE_DARK};
        font-weight: 700;
        letter-spacing: -0.02em;
        padding-top: 10px;
    }}

    /* Subtitle Styles */
    .pp-subtitle {{
        color: #4A4F5A;
        font-size: 1.05rem;
        margin-bottom: 2rem;
        text-align: center;
        max-width: 600px;
        margin-left: auto;
        margin-right: auto;
        line-height: 1.5;
    }}
    
    /* Streamlit Components */
    .stTextInput>div>div>input, 
    .stSelectbox>div>div, 
    .stNumberInput>div>div>input {{
        border: 2px solid {PP_BLUE_DARK} !important;
        border-radius: 8px;
        padding: 0.5rem 1rem;
    }}
    
    /* Button Styles */
    .stButton>button {{
        background-color: {PP_BLUE_DARK};
        color: white;
        border-radius: 20px;
        padding: 0.5rem 1.5rem;
        border: none;
        font-weight: 600;
        transition: background-color 0.3s;
    }}
    .stButton>button:hover {{
        background-color: {PP_BLUE_LIGHT};
        color: white;
    }}

    /* Expander Styles (for fee breakdowns) */
    .streamlit-expanderHeader {{
        background-color: #F8F8F8; /* Light gray background */
        border-radius: 8px;
        border-left: 5px solid {PP_BLUE_LIGHT};
        padding: 8px 15px;
        font-weight: 600;
        color: {PP_BLUE_DARK};
        margin-bottom: 10px;
    }}
    
    /* Result Card Styles (The comparison columns) */
    .result-card {{
        border: 1px solid #E0E0E0;
        border-radius: 12px;
        padding: 20px;
        margin-top: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        min-height: 550px;
        display: flex;
        flex-direction: column;
    }}
    
    /* Highlight the Dual Pricing option with the accent purple */
    .dual-pricing-card {{
        border: 2px solid {PP_ACCENT_PURPLE};
    }}
    
    .stAlert p {{
        color: {PP_BLUE_DARK} !important;
    }}
    
    /* Horizontal Rule */
    hr {{
        border-top: 2px solid #EEEEEE;
        margin: 2rem 0;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
#   LOGO + TITLE (Modern Header Block)
# -----------------------------
# Check if logo.png is present (Streamlit requirement)
if os.path.exists("logo.png"):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Assuming the logo is Pinpoint's logo (use a placeholder icon if not found)
        st.image("logo.png", width=220)
else:
    # Placeholder if logo.png is missing
    st.markdown(
        f"<div style='text-align:center; color:{PP_BLUE_DARK}; font-size:2.5rem; font-weight:900;'>PINPOINT PAYMENTS</div>",
        unsafe_allow_html=True
    )


st.markdown(
    f"<h2 style='text-align:center; margin-bottom:0.10rem; color:{PP_BLUE_DARK};'>Agent Revenue & Fees Calculator</h2>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p class='pp-subtitle'>Pinpoint your agent commissions. Compare <strong>Dual Pricing</strong> vs. "
    "<strong>Flat Rate</strong> with clear monthly, yearly, and one-time economics for your merchants.</p>",
    unsafe_allow_html=True,
)

# -----------------------------
#   MONTHLY VOLUME
# -----------------------------
st.markdown("### 📊 Merchant Volume")

volume_input = st.text_input("Enter Monthly Processing Volume ($)", value="15,000")


def parse_dollar_input(text: str) -> float:
    text = text.replace(",", "").replace("$", "").strip()
    if text == "":
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


volume = parse_dollar_input(volume_input)

# Profit assumptions (fixed) - DO NOT CHANGE FUNCTIONALITY
dual_profit_pct = 0.015       # 1.5% profit for Dual Pricing
flat_profit_pct = 0.01        # 1.0% profit for Flat Rate
revshare = 0.50               # 50% to agent

st.write("---")

# -----------------------------
#   MERCHANT SETUP
# -----------------------------
st.markdown("### ⚙️ Merchant Setup")

colA, colB = st.columns(2)

with colA:
    terminal = st.selectbox(
        "Terminal type",
        ["None", "Dejavoo P8", "Dejavoo P12 Mini"],
    )

    num_terminals = st.number_input(
        "Number of terminals", min_value=1, value=1, step=1
    )

with colB:
    needs_stand = False
    if terminal == "Dejavoo P8":
        needs_stand = st.checkbox("Add Dejavoo P8 stand? ($35 one-time)", value=False)

    # Mobile device count (default 0)
    num_mobile_devices = st.number_input(
        "Number of mobile devices (optional)",
        min_value=0,
        value=0,
        step=1,
        help="10 per month per device + 30 one-time download per device.",
    )

st.write("---")

# -----------------------------
#   FEE CONSTANTS
# -----------------------------
ACCOUNT_ON_FILE = 7.50
GATEWAY = 10.00
PER_TERMINAL_FIRST = 4.00
PER_TERMINAL_ADDITIONAL = 2.00
MOBILE_MONTHLY = 10.00

P8_TERMINAL = 310.00
P18_TERMINAL = 446.50
P12_TERMINAL = 166.75
STAND_P8 = 35.00
MOBILE_APP_DOWNLOAD = 30.00
DUAL_COMPLIANCE = 3.00  # one-time DP compliance fee (always applies to Dual Pricing)

# -----------------------------
#   ONE-TIME FEES (PER MERCHANT)
# -----------------------------
one_time_terminal = 0.0
if terminal == "Dejavoo P8":
    one_time_terminal = P8_TERMINAL
elif terminal == "Dejavoo P18":
    one_time_terminal = P18_TERMINAL
elif terminal == "Dejavoo P12 Mini":
    one_time_terminal = P12_TERMINAL

one_time_stand = STAND_P8 if (terminal == "Dejavoo P8" and needs_stand) else 0.0
one_time_mobile = num_mobile_devices * MOBILE_APP_DOWNLOAD

# Dual includes $3 compliance; Flat does not
dual_one_time_fees = one_time_terminal + one_time_stand + one_time_mobile + DUAL_COMPLIANCE
flat_one_time_fees = one_time_terminal + one_time_stand + one_time_mobile

# -----------------------------
#   MONTHLY FEES (PER MERCHANT)
# -----------------------------
monthly_account = ACCOUNT_ON_FILE
monthly_gateway = GATEWAY
monthly_first_terminal = PER_TERMINAL_FIRST
monthly_additional_terminals = max(num_terminals - 1, 0) * PER_TERMINAL_ADDITIONAL
monthly_mobile = num_mobile_devices * MOBILE_MONTHLY

monthly_fees_total = (
    monthly_account
    + monthly_gateway
    + monthly_first_terminal
    + monthly_additional_terminals
    + monthly_mobile
)

# All monthly fees are treated as "agent-responsible" in absorbing scenario
monthly_fees_agent = monthly_fees_total

# -----------------------------
#   PROFIT CALCULATIONS
# -----------------------------
dual_gross = volume * dual_profit_pct
flat_gross = volume * flat_profit_pct

dual_agent = dual_gross * revshare
flat_agent = flat_gross * revshare

dual_net_absorb = dual_agent - monthly_fees_agent
flat_net_absorb = flat_agent - monthly_fees_agent

dual_year_pass = dual_agent * 12
dual_year_absorb = dual_net_absorb * 12

flat_year_pass = flat_agent * 12
flat_year_absorb = flat_net_absorb * 12

# -----------------------------
#   RESULTS (SINGLE MERCHANT)
# -----------------------------
st.markdown(f"<h3 style='color:{PP_ACCENT_PURPLE};'>💰 Agent Commission Forecast</h3>", unsafe_allow_html=True)

colLeft, colRight = st.columns(2)

with colLeft:
    st.markdown(f'<div class="result-card dual-pricing-card">', unsafe_allow_html=True)
    st.subheader("Dual Pricing (3.99%)")
    st.write(f"**Gross Profit (Processor, Monthly):** ${dual_gross:,.2f}")
    st.write(f"**Agent Share (50%, Monthly):** ${dual_agent:,.2f}")

    # Monthly Fees Expander
    with st.expander(
        f"Monthly Fees (Total): ${monthly_fees_total:,.2f} — Click for Breakdown"
    ):
        st.markdown(f"- Account on file (bank): ${monthly_account:,.2f}")
        st.markdown(f"- Dejavoo gateway: ${monthly_gateway:,.2f}")
        st.markdown(f"- Dejavoo first terminal: ${monthly_first_terminal:,.2f}")
        if monthly_additional_terminals > 0:
            st.markdown(
                f"- Dejavoo additional terminals: ${monthly_additional_terminals:,.2f}"
            )
        if monthly_mobile > 0:
            st.markdown(
                f"- Dejavoo mobile devices: ${monthly_mobile:,.2f}"
            )

    st.markdown(f"<h4 style='color:{PP_ACCENT_PURPLE}; margin-top:10px;'>Net Commission Summary</h4>", unsafe_allow_html=True)
    st.markdown(f"**Net to Agent (Passing Monthly Fees):** <span style='font-size:1.25rem; font-weight:700; color:{PP_BLUE_DARK}'>${dual_agent:,.2f} / mo</span>", unsafe_allow_html=True)
    st.markdown(f"**Net to Agent (Absorbing Fees):** <span style='font-size:1.25rem; font-weight:700; color:{PP_BLUE_DARK}'>${dual_net_absorb:,.2f} / mo</span>", unsafe_allow_html=True)
    st.markdown(f"**Yearly Net (Passing Monthly Fees):** <span style='font-size:1.25rem; font-weight:700; color:{PP_BLUE_DARK}'>${dual_year_pass:,.2f}</span>", unsafe_allow_html=True)
    st.markdown(f"**Yearly Net (Absorbing Fees):** <span style='font-size:1.25rem; font-weight:700; color:{PP_BLUE_DARK}'>${dual_year_absorb:,.2f}</span>", unsafe_allow_html=True)


    # One-Time Fees Expander
    with st.expander(
        f"One-Time Setup Fees: ${dual_one_time_fees:,.2f} — Click for Breakdown"
    ):
        if one_time_terminal > 0:
            st.markdown(
                f"- Dejavoo terminal hardware: ${one_time_terminal:,.2f}"
            )
        if one_time_stand > 0:
            st.markdown(
                f"- Dejavoo P8 stand (if selected): ${one_time_stand:,.2f}"
            )
        if one_time_mobile > 0:
            st.markdown(
                f"- Dejavoo mobile app download ({num_mobile_devices} device(s)): "
                f"${one_time_mobile:,.2f}"
            )
        st.markdown(
            f"- Dual Pricing compliance fee: ${DUAL_COMPLIANCE:,.2f}"
        )
    st.markdown('</div>', unsafe_allow_html=True) # Close result-card

with colRight:
    st.markdown('<div class="result-card">', unsafe_allow_html=True)
    st.subheader("Flat Rate (2.95% + $0.30)")
    st.write(f"**Gross Profit (Processor, Monthly):** ${flat_gross:,.2f}")
    st.write(f"**Agent Share (50%, Monthly):** ${flat_agent:,.2f}")

    # Monthly Fees Expander
    with st.expander(
        f"Monthly Fees (Total): ${monthly_fees_total:,.2f} — Click for Breakdown"
    ):
        st.markdown(f"- Account on file (bank): ${monthly_account:,.2f}")
        st.markdown(f"- Dejavoo gateway: ${monthly_gateway:,.2f}")
        st.markdown(f"- Dejavoo first terminal: ${monthly_first_terminal:,.2f}")
        if monthly_additional_terminals > 0:
            st.markdown(
                f"- Dejavoo additional terminals: ${monthly_additional_terminals:,.2f}"
            )
        if monthly_mobile > 0:
            st.markdown(
                f"- Dejavoo mobile devices: ${monthly_mobile:,.2f}"
            )

    st.markdown(f"<h4 style='color:{PP_BLUE_DARK}; margin-top:10px;'>Net Commission Summary</h4>", unsafe_allow_html=True)
    st.markdown(f"**Net to Agent (Passing Monthly Fees):** <span style='font-size:1.25rem; font-weight:700; color:{PP_BLUE_DARK}'>${flat_agent:,.2f} / mo</span>", unsafe_allow_html=True)
    st.markdown(f"**Net to Agent (Absorbing Fees):** <span style='font-size:1.25rem; font-weight:700; color:{PP_BLUE_DARK}'>${flat_net_absorb:,.2f} / mo</span>", unsafe_allow_html=True)
    st.markdown(f"**Yearly Net (Passing Monthly Fees):** <span style='font-size:1.25rem; font-weight:700; color:{PP_BLUE_DARK}'>${flat_year_pass:,.2f}</span>", unsafe_allow_html=True)
    st.markdown(f"**Yearly Net (Absorbing Fees):** <span style='font-size:1.25rem; font-weight:700; color:{PP_BLUE_DARK}'>${flat_year_absorb:,.2f}</span>", unsafe_allow_html=True)


    # One-Time Fees Expander
    with st.expander(
        f"One-Time Setup Fees: ${flat_one_time_fees:,.2f} — Click for Breakdown"
    ):
        if one_time_terminal > 0:
            st.markdown(
                f"- Dejavoo terminal hardware: ${one_time_terminal:,.2f}"
            )
        if one_time_stand > 0:
            st.markdown(
                f"- Dejavoo P8 stand (if selected): ${one_time_stand:,.2f}"
            )
        if one_time_mobile > 0:
            st.markdown(
                f"- Dejavoo mobile app download ({num_mobile_devices} device(s)): "
                f"${one_time_mobile:,.2f}"
            )
        st.markdown(
            "- Dual Pricing compliance fee: $0.00 (not charged on flat rate)"
        )
    st.markdown('</div>', unsafe_allow_html=True) # Close result-card


# -----------------------------
#   DISCLAIMER
# -----------------------------
st.write("---")
st.markdown(
    "_Disclaimer: These are only estimates. BIN mix and method of processing "
    "(Card Not Present, Swipe, MOTO) can all change the exact profit for any merchant._"
)
