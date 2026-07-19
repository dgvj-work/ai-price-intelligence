"""Cortex Cost Advisor - insight-first Streamlit entrypoint."""

from __future__ import annotations

import streamlit as st

from screens import about, advisor, getting_started, model_advisor, overview, price_watch
from session_data import (
    APP_VERSION,
    humanize_source,
    init_usage_session,
    load_persisted_credit_price,
    needs_setup,
    persist_credit_price,
)
from theme import apply_theme

st.set_page_config(
    page_title="Cortex Cost Advisor",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = {
    "Getting started": getting_started.render,
    "Advisor": advisor.render,
    "Switches": model_advisor.render,
    "Price Watch": price_watch.render,
    "Spend detail": overview.render,
    "Trust": about.render,
}

SUPPORT_URL = "https://github.com/dgvj-work/ai-price-intelligence/discussions"


def main() -> None:
    apply_theme()

    with st.sidebar:
        st.markdown("### Cortex Cost Advisor")
        st.caption(f"v{APP_VERSION}")
        st.caption("Recommendations, not just reports")

        # Thin ACCOUNT_USAGE views are (re)bound silently once per session.
        init_usage_session()

        if "credit_price_loaded" not in st.session_state:
            st.session_state["credit_price_usd"] = load_persisted_credit_price(3.0)
            st.session_state["credit_price_loaded"] = True

        source = st.session_state.get("usage_source")
        st.divider()
        st.caption("Data status")
        if needs_setup(source):
            st.warning("Preview sample")
        else:
            label = humanize_source(source)
            st.success(f"Live | {label}" if label else "Live Cortex metering")

        page_names = list(PAGES.keys())
        default_page = "Getting started" if needs_setup(source) else "Advisor"
        page = st.radio(
            "Navigate",
            page_names,
            index=page_names.index(default_page),
            key="main_nav",
        )

        st.divider()
        st.markdown("#### Planning inputs")
        credit_price = st.number_input(
            "Your credit rate ($ / credit)",
            min_value=0.01,
            max_value=100.0,
            value=float(st.session_state.get("credit_price_usd", 3.0)),
            step=0.05,
            help=(
                "Snowflake apps cannot read your contracted credit price. "
                "Enter the rate from your invoice or capacity contract. "
                "Saved inside this app's schema for next visits. Never exported."
            ),
            key="credit_price_input",
        )
        st.caption("USD amounts are estimates. Credits stay accurate.")
        if abs(float(credit_price) - float(st.session_state.get("credit_price_usd", 3.0))) > 1e-9:
            persist_credit_price(float(credit_price))
        st.session_state["credit_price_usd"] = float(credit_price)

        days = st.selectbox(
            "Analysis window (days)",
            options=[30, 60, 90, 180, 365],
            index=2,
            help="Up to 365 days from ACCOUNT_USAGE retention via app views.",
        )
        st.session_state["days"] = int(days)

        if needs_setup(source):
            st.divider()
            if st.button("I granted privileges; connect", use_container_width=True):
                st.cache_data.clear()
                init_usage_session(force=True)
                st.rerun()

        st.divider()
        st.caption("For FinOps / platform teams")
        st.markdown("Decide which Cortex models to allow or migrate.")
        st.caption("Publisher: Digvijay Vaghela")
        st.markdown(f"[GitHub Discussions]({SUPPORT_URL})")

    PAGES[page]()


if __name__ == "__main__":
    main()
