"""Cortex Cost Advisor - insight-first Streamlit entrypoint."""

from __future__ import annotations

import streamlit as st

from insights import SWITCH_MIN_SAVINGS_PCT
from screens import about, advisor, getting_started, model_advisor, overview, price_watch
from session_data import (
    APP_VERSION,
    GRANT_SQL,
    SUPPORT_EMAIL,
    SUPPORT_URL,
    connect_live_usage,
    connection_status_label,
    init_usage_session,
    last_connect_result,
    load_persisted_credit_price,
    load_persisted_min_savings_pct,
    needs_setup,
    persist_credit_price,
    persist_min_savings_pct,
)
from theme import apply_theme, brand_header

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


def main() -> None:
    apply_theme()

    with st.sidebar:
        brand_header()
        st.caption(f"v{APP_VERSION}")

        # Thin ACCOUNT_USAGE views are (re)bound silently once per session.
        init_usage_session()

        if "credit_price_loaded" not in st.session_state:
            st.session_state["credit_price_usd"] = load_persisted_credit_price(3.0)
            st.session_state["credit_price_loaded"] = True
        if "min_savings_loaded" not in st.session_state:
            st.session_state["min_switch_savings_pct"] = load_persisted_min_savings_pct(
                SWITCH_MIN_SAVINGS_PCT * 100.0
            )
            st.session_state["min_savings_loaded"] = True

        source = st.session_state.get("usage_source")
        st.divider()
        st.caption("Data status")
        if needs_setup(source):
            st.warning(connection_status_label(source))
            st.caption(
                "Advisor is usable now on **sample** data. "
                "Live metering needs a one-time ACCOUNTADMIN GRANT."
            )
            attempt = last_connect_result()
            if attempt and not attempt.get("connected"):
                st.caption(attempt["message"])
        else:
            st.success(connection_status_label(source))

        page_names = list(PAGES.keys())
        # Preserve nav choice across reruns; default only when unset.
        if "main_nav" not in st.session_state:
            st.session_state["main_nav"] = (
                "Getting started" if needs_setup(source) else "Advisor"
            )
        page = st.radio(
            "Navigate",
            page_names,
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

        min_pct = st.slider(
            "Min switch savings to surface (%)",
            min_value=5,
            max_value=50,
            value=int(round(float(st.session_state.get("min_switch_savings_pct", 15.0)))),
            step=5,
            help=(
                "Only recommend model switches at least this % cheaper at list rates. "
                "Default 15%. Many FinOps teams act only on 25%+ savings."
            ),
            key="min_savings_slider",
        )
        if abs(float(min_pct) - float(st.session_state.get("min_switch_savings_pct", 15.0))) > 1e-9:
            persist_min_savings_pct(float(min_pct))
        st.session_state["min_switch_savings_pct"] = float(min_pct)

        days = st.selectbox(
            "Analysis window (days)",
            options=[30, 60, 90, 180, 365],
            index=2,
            help="Up to 365 days from ACCOUNT_USAGE retention via app views.",
        )
        st.session_state["days"] = int(days)

        if needs_setup(source):
            st.divider()
            st.markdown("#### Connect live data")
            st.caption("Step 1: run GRANT in a Worksheet (ACCOUNTADMIN)")
            st.code(GRANT_SQL, language="sql")
            if st.button("Step 2: Connect live usage", use_container_width=True, type="primary"):
                result = connect_live_usage()
                if result["connected"]:
                    st.success(result["message"])
                    st.session_state["main_nav"] = "Advisor"
                    st.rerun()
                else:
                    st.error(result["message"])

        st.divider()
        st.caption("Support")
        st.markdown(f"[GitHub Discussions]({SUPPORT_URL})")
        st.caption(f"Publisher contact: [{SUPPORT_EMAIL}](mailto:{SUPPORT_EMAIL})")

    PAGES[page]()


if __name__ == "__main__":
    main()
