"""Advisor home - lead with recommendations, not raw credit tables."""

from __future__ import annotations

import streamlit as st

from charts import switch_savings_bars
from insights import build_advisor_pack
from screens.setup import render_connect_account
from session_data import (
    APP_VERSION,
    load_cortex_spend,
    load_ref_cortex_current,
    load_snapshot,
    load_usage_by_model,
    mode_banner,
)
from theme import hero, metric_strip, recommendation_card, section


def _cortex_price_table():
    prices = load_ref_cortex_current()
    if not prices.empty:
        return prices, True
    snap = load_snapshot()
    cortex = snap[snap["row_type"] == "cortex"].copy()
    if cortex.empty:
        return cortex, False
    # Select only Cortex rate columns - CSV also has empty LLM columns that collide on rename.
    return (
        cortex[["cortex_function", "cortex_model", "credits_per_1m_tokens"]]
        .rename(
            columns={
                "cortex_function": "FUNCTION_NAME",
                "cortex_model": "MODEL_NAME",
                "credits_per_1m_tokens": "CREDITS_PER_1M_TOKENS",
            }
        ),
        False,
    )


def render() -> None:
    hero(
        "Stop guessing which Cortex model is burning budget",
        "Ranked model-switch savings, concentration and spend spikes, and a forward "
        "Cortex cost estimate: decisions Snowsight rollups do not make for you.",
        kicker=f"Advisor | v{APP_VERSION}",
    )

    days = int(st.session_state.get("days", 90))
    credit_price = float(st.session_state.get("credit_price_usd", 3.0))

    usage, mode = load_usage_by_model(days)
    spend, _ = load_cortex_spend(days)
    prices, from_dataset = _cortex_price_table()
    snap = load_snapshot()
    llm = snap[snap["row_type"] == "llm"] if not snap.empty else snap

    mode_banner(mode)

    pack = build_advisor_pack(
        usage=usage,
        spend=spend,
        cortex_prices=prices,
        llm_snapshot=llm,
        credit_price=credit_price,
    )

    primary = pack["primary"]
    if primary is not None:
        recommendation_card(primary, lead=True)
    else:
        st.info(
            "**Status**: No switch savings above threshold in this window. "
            "Either usage is already on efficient models, or rates/usage are sparse. "
            "Check Spend for detail and Price Watch for external list moves."
        )

    total_credits = float(usage["CREDITS"].sum()) if not usage.empty else 0.0
    spark = None
    if not spend.empty and "DAY" in spend.columns and "CREDITS" in spend.columns:
        spark = spend.groupby("DAY", as_index=False)["CREDITS"].sum().sort_values("DAY")["CREDITS"]
    section("At a glance")
    metric_strip(
        [
            (
                "Switch savings (est. USD)",
                f"${pack['total_switch_savings_usd']:,.0f}",
                "Sum of ranked list-rate switch scenarios >=15% cheaper. Estimate only.",
            ),
            (
                "Switch opportunities",
                f"{len(pack['switches'])}",
                "Models where an alternate Cortex list rate beats your effective spend.",
            ),
            (
                f"Cortex credits ({days}d)",
                f"{total_credits:,.1f}",
                "Context only. USD elsewhere uses your contract $/credit input.",
            ),
        ],
        spark=spark,
    )
    st.caption(
        f"USD uses your sidebar rate (${credit_price:.2f}/credit). "
        "Planning estimates, not invoices. "
        + (
            "Rates: Marketplace dataset."
            if from_dataset
            else "Rates: bundled Cortex credit snapshot."
        )
    )

    switches = pack.get("switches") or []
    if switches:
        section("Top switch savings", "Ranked list-rate scenarios for this window.")
        bar_rows = []
        for insight in switches[:6]:
            meta = getattr(insight, "meta", None) or {}
            frm = meta.get("from_model", "?")
            to = meta.get("to_model", "?")
            bar_rows.append(
                {
                    "label": f"{frm} -> {to}",
                    "usd": float(getattr(insight, "savings_usd", 0) or 0),
                    "credits": float(getattr(insight, "savings_credits", 0) or 0),
                }
            )
        switch_savings_bars(bar_rows)

    if pack["secondary"]:
        section("More findings", "Supporting signals (compact). Primary recommendation is above.")
        secondary = pack["secondary"][:6]
        for i in range(0, len(secondary), 2):
            left, right = st.columns(2)
            with left:
                recommendation_card(secondary[i])
            if i + 1 < len(secondary):
                with right:
                    recommendation_card(secondary[i + 1])

    with st.expander("How this differs from raw SQL / Snowsight"):
        st.markdown(
            """
| What you can do alone | What Advisor adds |
|----------------------|-------------------|
| **SELECT** credits from ACCOUNT_USAGE | **Ranked switch recommendations** with $ impact |
| Snowsight account credit charts | **Concentration + spike detection** on Cortex only |
| Manual spreadsheet model compare | **Same-token scenarios** against Cortex list rates |
| Nothing built-in for public LLM moves | **Price Watch** overlap against models you used |

Buyer: FinOps / platform engineers deciding **which Cortex models to allow or migrate**.
            """
        )

    render_connect_account()
