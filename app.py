"""
Network Token ROI Simulator
Status: Work in progress

Models 12-month net ROI of network tokenization rollout for multi-country
merchants, calibrated on public 2026 benchmarks (Mastercard, Visa, Adyen).
"""

import streamlit as st

st.set_page_config(
    page_title="Network Token ROI Simulator",
    page_icon="🔐",
    layout="wide",
)

st.title("🔐 Network Token ROI Simulator")
st.caption(
    "Modeling network tokenization rollout ROI for multi-country merchants"
)

st.info(
    "🚧 Work in progress — iterating based on feedback from payments PMs. "
    "Reach out on LinkedIn for read-only access discussions."
)

st.markdown("---")

st.markdown("### Inputs (coming soon)")
st.markdown("- Monthly volume by country")
st.markdown("- CIT / MIT transaction split")
st.markdown("- Baseline authorization rate")
st.markdown("- PSP scenario selector")

st.markdown("### Calibration sources")
st.markdown(
    "- Mastercard × Checkout.com whitepaper (April 2026)\n"
    "- Visa tokenized CNP authorization data\n"
    "- Adyen Uplift / Personalize 2026 launch data"
)

st.markdown("### Outputs (coming soon)")
st.markdown("- 12-month net ROI by PSP scenario")
st.markdown("- Sensitivity analysis on issuer enablement gap")
st.markdown("- Approval rate uplift breakdown (CIT vs MIT)")
st.markdown("- Fraud chargeback reduction estimate")