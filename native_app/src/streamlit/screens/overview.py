"""Spend detail — supporting evidence for Advisor recommendations."""

from __future__ import annotations

import streamlit as st

from screens.setup import render_connect_account
from session_data import load_cortex_spend, load_cortex_top, load_metering, mode_banner
from theme import hero


def render() -> None:
    hero(
        "Spend detail",
        "Supporting charts for the Advisor recommendations. Start on **Advisor** for "
        "what to do; use this page when you need the underlying Cortex trend.",
        kicker="Evidence",
    )

    days = int(st.session_state.get("days", 90))
    credit_price = float(st.session_state.get("credit_price_usd", 3.0))

    spend, spend_mode = load_cortex_spend(days)
    top, top_mode = load_cortex_top(days)
    modes = {spend_mode, top_mode}
    if "error" in modes:
        mode = "error"
    elif "live" in modes:
        mode = "live"
    elif "sample" in modes:
        mode = "sample"
    else:
        mode = "preview"
    mode_banner(mode)

    if mode == "live" and spend.empty and top.empty:
        metering, m_mode = load_metering(days)
        if m_mode == "live" and not metering.empty:
            st.caption("Function-level Cortex rows empty — AI/Cortex metering fallback.")
            total_credits = float(metering["CREDITS"].sum())
            c1, c2 = st.columns(2)
            c1.metric("Credits (metering)", f"{total_credits:,.2f}")
            c2.metric("USD estimate*", f"${total_credits * credit_price:,.2f}")
            st.line_chart(
                metering.groupby("DAY", as_index=False)["CREDITS"].sum(),
                x="DAY",
                y="CREDITS",
            )
            st.dataframe(metering, use_container_width=True)
            st.caption("*USD estimate uses your sidebar $/credit — not an invoice.")
            render_connect_account()
            return

    total_credits = float(spend["CREDITS"].sum()) if not spend.empty else float(top["CREDITS"].sum())
    total_tokens = float(spend["TOKENS"].sum()) if not spend.empty else float(top["TOKENS"].sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Cortex credits", f"{total_credits:,.2f}")
    c2.metric("USD estimate*", f"${total_credits * credit_price:,.2f}")
    c3.metric("Tokens", f"{total_tokens:,.0f}")

    if not spend.empty:
        daily = spend.groupby("DAY", as_index=False)["CREDITS"].sum()
        st.subheader("Daily trend")
        st.line_chart(daily, x="DAY", y="CREDITS")

    st.subheader("Top functions / models")
    if top.empty:
        st.caption("No per-function breakdown in this window.")
    else:
        top_view = top.copy()
        top_view["USD_EST"] = top_view["CREDITS"] * credit_price
        st.dataframe(top_view, use_container_width=True)

    st.caption(
        f"Window: {days} days (up to 365). ACCOUNT_USAGE can lag ~45 minutes. "
        "*USD uses your contract $/credit input — planning estimate only."
    )
    render_connect_account()
