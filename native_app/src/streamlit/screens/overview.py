"""Overview — value first, then metrics (live or preview), then optional connect."""

from __future__ import annotations

import streamlit as st

from screens.setup import render_connect_account
from session_data import (
    load_cortex_spend,
    load_cortex_top,
    load_metering,
    mode_banner,
)


def _value_prop() -> None:
    st.title("Cortex Cost Advisor")
    st.markdown(
        """
Snowflake’s built-in cost UI shows **account-wide** credits. This app is different:
it is built for **Cortex / AI function** FinOps — model-level spend, switch scenarios,
and public list-price moves that affect the models you already call.
        """
    )
    a, b, c = st.columns(3)
    with a:
        st.markdown("**Overview**")
        st.caption("Cortex credits, USD estimate, trend, and top functions/models.")
    with b:
        st.markdown("**Model Advisor**")
        st.caption("“Same tokens, different Cortex model — what would credits be?”")
    with c:
        st.markdown("**Price Watch**")
        st.caption("Public LLM list-price moves, flagged against models you use.")


def _why_not_snowsight() -> None:
    with st.expander("Why install this instead of only using Snowsight cost tools?"):
        st.markdown(
            """
| Snowsight / native tooling | Cortex Cost Advisor |
|----------------------------|---------------------|
| Account & warehouse credit rollups, budgets, resource monitors | **Cortex function + model** credit breakdown |
| Not built for “switch model X → Y” planning | **Model Advisor** scenarios from your token volumes |
| No public LLM price-change overlay | **Price Watch** against Marketplace or bundled rates |
| Data stays in Snowflake | Same — **zero egress**, read-only, inspectable code |

Use Snowsight for platform FinOps. Use this app when Cortex is a material line item
and you need model-level decisions.
            """
        )


def render() -> None:
    _value_prop()

    days = int(st.session_state.get("days", 90))
    credit_price = float(st.session_state.get("credit_price_usd", 3.0))

    spend, spend_mode = load_cortex_spend(days)
    top, top_mode = load_cortex_top(days)
    if spend_mode == "live" or top_mode == "live":
        mode = "live"
    elif spend_mode == "sample" or top_mode == "sample":
        mode = "sample"
    else:
        mode = "preview"
    mode_banner(mode)

    # Prefer Cortex detail; if live but empty, try metering before falling back
    # (load_* already falls back to preview when privileges missing).
    if mode == "live" and spend.empty and top.empty:
        metering, m_mode = load_metering(days)
        if m_mode == "live" and not metering.empty:
            st.caption(
                "Cortex function detail is empty in this window — showing AI/Cortex "
                "metering service types instead. ACCOUNT_USAGE can lag ~45 minutes."
            )
            total_credits = float(metering["CREDITS"].sum())
            c1, c2 = st.columns(2)
            c1.metric("Credits (metering)", f"{total_credits:,.2f}")
            c2.metric("USD estimate", f"${total_credits * credit_price:,.2f}")
            st.subheader("Spend trend")
            st.line_chart(
                metering.groupby("DAY", as_index=False)["CREDITS"].sum(),
                x="DAY",
                y="CREDITS",
            )
            st.dataframe(metering, use_container_width=True)
            _why_not_snowsight()
            render_connect_account()
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
        st.info("No per-function breakdown in this window yet.")
    else:
        top_view = top.copy()
        top_view["USD_EST"] = top_view["CREDITS"] * credit_price
        st.dataframe(top_view, use_container_width=True)

    st.caption(
        "Window capped at 90 days. ACCOUNT_USAGE metering can lag live activity by up to ~45 minutes. "
        "USD uses the credit price from the sidebar (session-only; default $3.00)."
    )

    _why_not_snowsight()
    render_connect_account()
