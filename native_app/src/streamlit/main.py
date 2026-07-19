"""Cortex Cost Advisor — multi-page Streamlit entrypoint."""

from __future__ import annotations

import streamlit as st

from screens import about, model_advisor, overview, price_watch
from session_data import ensure_usage_views

st.set_page_config(
    page_title="Cortex Cost Advisor",
    page_icon="❄️",
    layout="wide",
)

PAGES = {
    "Overview": overview.render,
    "Model Advisor": model_advisor.render,
    "Price Watch": price_watch.render,
    "About / Trust": about.render,
}


def main() -> None:
    st.sidebar.title("Cortex Cost Advisor")
    st.sidebar.caption("Read-only · stays in your account")

    if st.sidebar.button("Refresh usage views", help="Re-run after granting imported privileges"):
        st.cache_data.clear()
        source = ensure_usage_views()
        st.session_state["usage_source"] = source
        st.sidebar.success(f"Views refreshed ({source})")

    if "usage_source" not in st.session_state:
        st.session_state["usage_source"] = ensure_usage_views()

    page = st.sidebar.radio("Navigate", list(PAGES.keys()), index=0)
    credit_price = st.sidebar.number_input(
        "Snowflake credit price (USD)",
        min_value=0.01,
        max_value=100.0,
        value=3.00,
        step=0.05,
        help="Used only for USD estimates in this session. Default $3.00.",
    )
    days = st.sidebar.selectbox("Window (days)", options=[30, 60, 90], index=2)
    st.session_state["credit_price_usd"] = float(credit_price)
    st.session_state["days"] = int(days)
    PAGES[page]()


if __name__ == "__main__":
    main()
