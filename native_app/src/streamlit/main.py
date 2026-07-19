"""Cortex Cost Advisor — multi-page Streamlit entrypoint."""

from __future__ import annotations

import streamlit as st

from screens import about, model_advisor, overview, price_watch
from session_data import (
    APP_VERSION,
    humanize_source,
    init_usage_session,
    needs_setup,
)

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
    st.sidebar.caption(f"v{APP_VERSION} · Read-only · zero egress")

    # Auto-refresh usage views on every new session (no manual click required).
    init_usage_session()

    source = st.session_state.get("usage_source")
    if needs_setup(source):
        st.sidebar.caption("Mode: **Preview** (sample data)")
        st.sidebar.caption("Connect live usage from Overview when ready.")
    else:
        label = humanize_source(source) or "live metering"
        st.sidebar.caption(f"Mode: **Live** · {label}")

    page = st.sidebar.radio("Navigate", list(PAGES.keys()), index=0)

    credit_price = st.sidebar.number_input(
        "Snowflake credit price (USD)",
        min_value=0.01,
        max_value=100.0,
        value=3.00,
        step=0.05,
        help="Session-only USD estimates. Default $3.00. Not written anywhere.",
    )
    days = st.sidebar.selectbox("Window (days)", options=[30, 60, 90], index=2)
    st.session_state["credit_price_usd"] = float(credit_price)
    st.session_state["days"] = int(days)

    with st.sidebar.expander("Advanced"):
        st.caption(
            "Views refresh automatically when you open the app. "
            "Use this only if an admin just granted privileges."
        )
        if st.button("Re-check privileges / refresh views"):
            st.cache_data.clear()
            init_usage_session(force=True)
            new_source = st.session_state.get("usage_source")
            if needs_setup(new_source):
                st.warning("Still in preview — privilege not detected yet.")
            else:
                st.success(f"Live · {humanize_source(new_source)}")
                st.rerun()

    st.sidebar.divider()
    st.sidebar.markdown(
        f"""
**Trust**  
Publisher: Digvijay Vaghela  
Support: digvijay.vaghela@yahoo.com  
Source: [GitHub](https://github.com/dgvj-work/ai-price-intelligence)  
Updates: app patches as needed · prices weekly (optional dataset)
        """
    )

    PAGES[page]()


if __name__ == "__main__":
    main()
