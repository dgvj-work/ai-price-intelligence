"""Overview — Cortex spend, trends, top functions."""

from __future__ import annotations

import streamlit as st

from screens.setup import render_setup_panel
from session_data import (
    empty_state,
    humanize_source,
    load_cortex_spend,
    load_cortex_top,
    load_metering,
)


def render() -> None:
    st.title("Overview")
    st.caption(
        "Your Cortex / AI spend from Snowflake ACCOUNT_USAGE — credits, trends, "
        "and top functions. Window capped at 90 days."
    )

    if render_setup_panel():
        return

    days = int(st.session_state.get("days", 90))
    credit_price = float(st.session_state.get("credit_price_usd", 3.0))
    source_label = humanize_source(st.session_state.get("usage_source"))
    if source_label:
        st.caption(f"Reading: {source_label}")

    st.info(
        "**Data lag:** ACCOUNT_USAGE metering can lag up to ~45 minutes behind "
        "live activity. Use **Refresh usage data** in the sidebar after new Cortex calls. "
        "Also explore **Model Advisor** (switch-cost scenarios) and **Price Watch** "
        "(list-price moves on models you use)."
    )

    spend = load_cortex_spend(days)
    top = load_cortex_top(days)

    if spend.empty and top.empty:
        metering = load_metering(days)
        if metering.empty:
            empty_state(
                f"No Cortex / AI usage found in the last {days} days. "
                "If Cortex is enabled, run AI functions and check back after the "
                "ACCOUNT_USAGE lag (~45 minutes). Model Advisor and Price Watch still "
                "work with the bundled price snapshot."
            )
            with st.expander("What the other pages do"):
                st.markdown(
                    """
- **Model Advisor** — estimate credits if the same token volume ran on another Cortex model.
- **Price Watch** — recent public list-price changes, highlighted when they match models you use.
- **About / Trust** — exactly what is read, why the privilege is needed, and what never happens.
                    """
                )
            return
        st.warning(
            "Detailed Cortex AI function rows are empty — showing metering fallback "
            "(AI_SERVICES / Cortex-related service types)."
        )
        total_credits = float(metering["CREDITS"].sum())
        c1, c2 = st.columns(2)
        c1.metric("Credits (metering)", f"{total_credits:,.2f}")
        c2.metric("USD estimate", f"${total_credits * credit_price:,.2f}")
        st.line_chart(
            metering.groupby("DAY", as_index=False)["CREDITS"].sum(), x="DAY", y="CREDITS"
        )
        st.dataframe(metering, use_container_width=True)
        return

    total_credits = float(spend["CREDITS"].sum()) if not spend.empty else float(top["CREDITS"].sum())
    total_tokens = float(spend["TOKENS"].sum()) if not spend.empty else float(top["TOKENS"].sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Cortex credits", f"{total_credits:,.2f}")
    c2.metric("USD estimate", f"${total_credits * credit_price:,.2f}")
    c3.metric("Tokens", f"{total_tokens:,.0f}")

    if not spend.empty:
        daily = spend.groupby("DAY", as_index=False)["CREDITS"].sum()
        st.subheader("Spend trend")
        st.line_chart(daily, x="DAY", y="CREDITS")

    st.subheader("Top functions / models")
    if top.empty:
        empty_state("No per-function breakdown available.")
    else:
        top = top.copy()
        top["USD_EST"] = top["CREDITS"] * credit_price
        st.dataframe(top, use_container_width=True)
