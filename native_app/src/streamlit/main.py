"""Cortex Cost Advisor — insight-first Streamlit entrypoint."""

from __future__ import annotations

import streamlit as st

from screens import about, advisor, model_advisor, overview, price_watch
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
    "Advisor": advisor.render,
    "Switches": model_advisor.render,
    "Price Watch": price_watch.render,
    "Spend detail": overview.render,
    "Trust": about.render,
}


def main() -> None:
    apply_theme()
    st.sidebar.markdown("### Cortex Cost Advisor")
    st.sidebar.caption(f"v{APP_VERSION} · recommendations, not just reports")

    # Thin ACCOUNT_USAGE views are (re)bound silently once per session.
    init_usage_session()

    if "credit_price_loaded" not in st.session_state:
        st.session_state["credit_price_usd"] = load_persisted_credit_price(3.0)
        st.session_state["credit_price_loaded"] = True

    source = st.session_state.get("usage_source")
    if needs_setup(source):
        st.sidebar.caption("Data: preview sample")
    else:
        label = humanize_source(source)
        st.sidebar.caption(
            f"Data: live · {label}" if label else "Data: live Cortex metering"
        )

    page = st.sidebar.radio("Navigate", list(PAGES.keys()), index=0)

    st.sidebar.markdown("#### Planning inputs")
    credit_price = st.sidebar.number_input(
        "Your credit rate ($ / credit)",
        min_value=0.01,
        max_value=100.0,
        value=float(st.session_state.get("credit_price_usd", 3.0)),
        step=0.05,
        help=(
            "Snowflake apps cannot read your contracted credit price. "
            "Enter the rate from your invoice or capacity contract. "
            "Saved inside this app’s schema for next visits — never exported."
        ),
        key="credit_price_input",
    )
    st.sidebar.caption(
        "USD amounts are **estimates**. Wrong rate ⇒ wrong dollars; credits stay accurate."
    )
    if abs(float(credit_price) - float(st.session_state.get("credit_price_usd", 3.0))) > 1e-9:
        persist_credit_price(float(credit_price))
    st.session_state["credit_price_usd"] = float(credit_price)

    days = st.sidebar.selectbox(
        "Analysis window (days)",
        options=[30, 60, 90, 180, 365],
        index=2,
        help="Up to 365 days from ACCOUNT_USAGE retention via app views.",
    )
    st.session_state["days"] = int(days)

    st.sidebar.divider()
    st.sidebar.markdown(
        """
**For FinOps / platform teams**  
Decide which Cortex models to allow or migrate.

Publisher: Digvijay Vaghela  
Support: digvijay.vaghela@yahoo.com  
[Source on GitHub](https://github.com/dgvj-work/ai-price-intelligence)
        """
    )

    if needs_setup(source):
        if st.sidebar.button("I granted privileges — connect"):
            st.cache_data.clear()
            init_usage_session(force=True)
            st.rerun()

    PAGES[page]()


if __name__ == "__main__":
    main()
