"""Switch scenarios — full ranked table behind Advisor headlines."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from insights import switch_recommendations
from screens.setup import render_connect_account
from session_data import (
    load_ref_cortex_current,
    load_snapshot,
    load_usage_by_model,
    mode_banner,
)
from theme import hero, recommendation_card


def render() -> None:
    hero(
        "Model switch scenarios",
        "Same tokens, different Cortex list rates. Advisor surfaces the top savings; "
        "this page is the full scenario matrix for FinOps review.",
        kicker="Switches",
    )

    days = int(st.session_state.get("days", 90))
    credit_price = float(st.session_state.get("credit_price_usd", 3.0))
    usage, mode = load_usage_by_model(days)
    mode_banner(mode)

    cortex_prices = load_ref_cortex_current()
    using_dataset = not cortex_prices.empty
    if not using_dataset:
        snap = load_snapshot()
        cortex_prices = snap[snap["row_type"] == "cortex"].copy()
        if not cortex_prices.empty:
            cortex_prices = cortex_prices[
                ["cortex_function", "cortex_model", "credits_per_1m_tokens"]
            ].rename(
                columns={
                    "cortex_function": "FUNCTION_NAME",
                    "cortex_model": "MODEL_NAME",
                    "credits_per_1m_tokens": "CREDITS_PER_1M_TOKENS",
                }
            )
        st.caption("Using bundled Cortex credit rates (bind Marketplace dataset for weekly updates).")
    else:
        st.caption("Using bound Marketplace Cortex rates.")

    recs = switch_recommendations(usage, cortex_prices, credit_price)
    if recs:
        st.subheader("Ranked recommendations")
        for insight in recs[:5]:
            recommendation_card(insight)
    else:
        st.caption("No switch ≥15% cheaper than current effective spend in this window.")

    st.subheader("Usage basis")
    usage_view = usage.copy()
    usage_view["USD_EST"] = usage_view["CREDITS"] * credit_price
    st.dataframe(usage_view, use_container_width=True)

    if cortex_prices.empty:
        st.caption("No Cortex rate table available.")
        render_connect_account()
        return

    st.subheader("Full scenario matrix")
    cp = cortex_prices.copy()
    cp.columns = [c.upper() for c in cp.columns]
    rows: list[dict[str, object]] = []
    for _, u in usage.iterrows():
        tokens = float(u.get("TOKENS") or 0)
        current_model = str(u.get("MODEL_NAME") or "")
        fn = str(u.get("FUNCTION_NAME") or "COMPLETE")
        actual_credits = float(u.get("CREDITS") or 0)
        candidates = cp[cp["FUNCTION_NAME"].astype(str).str.upper() == fn.upper()]
        if candidates.empty:
            candidates = cp[cp["FUNCTION_NAME"].astype(str).str.upper() == "COMPLETE"]
        for _, alt in candidates.iterrows():
            alt_model = str(alt.get("MODEL_NAME"))
            rate = float(alt.get("CREDITS_PER_1M_TOKENS") or 0)
            est = tokens / 1_000_000.0 * rate
            rows.append(
                {
                    "YOUR_MODEL": current_model,
                    "FUNCTION": fn,
                    "YOUR_TOKENS": tokens,
                    "YOUR_CREDITS": actual_credits,
                    "ALT_MODEL": alt_model,
                    "ALT_CREDITS_EST": round(est, 4),
                    "CREDIT_DELTA": round(est - actual_credits, 4),
                    "USD_DELTA": round((est - actual_credits) * credit_price, 2),
                }
            )
    if not rows:
        st.caption("Could not build scenarios.")
        render_connect_account()
        return

    scen = pd.DataFrame(rows)
    scen = scen[scen["YOUR_MODEL"].str.lower() != scen["ALT_MODEL"].str.lower()]
    st.dataframe(scen.sort_values("USD_DELTA"), use_container_width=True)
    st.caption(
        "Negative USD_DELTA = cheaper alternate at list rates. "
        "Validate quality before migrating. USD = estimate from your $/credit."
    )
    render_connect_account()
