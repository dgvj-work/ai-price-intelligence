"""Overview — Cortex spend, trends, top functions."""

from __future__ import annotations

import streamlit as st

from session_data import empty_state, load_cortex_spend, load_cortex_top, load_metering


def render() -> None:
    st.title("Overview")
    st.caption("Cortex / AI spend from ACCOUNT_USAGE (window capped at 90 days).")

    days = int(st.session_state.get("days", 90))
    credit_price = float(st.session_state.get("credit_price_usd", 3.0))
    source = st.session_state.get("usage_source")
    if source:
        st.caption(f"Usage view source: `{source}`")

    spend = load_cortex_spend(days)
    top = load_cortex_top(days)

    if spend.empty and top.empty:
        metering = load_metering(days)
        if metering.empty:
            empty_state(
                "No Cortex usage found in the last "
                f"{days} days. Grant **Imported Privileges on SNOWFLAKE DB**, then use "
                "**Refresh usage views** in the sidebar. "
                "If this is a new account or Cortex isn’t enabled yet, run AI functions and "
                "check back (ACCOUNT_USAGE can lag)."
            )
            return
        st.warning(
            "Cortex AI function usage views are empty — showing metering fallback "
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
