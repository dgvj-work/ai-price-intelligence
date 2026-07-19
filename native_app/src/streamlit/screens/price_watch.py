"""Price Watch — public list moves that affect models you use."""

from __future__ import annotations

import streamlit as st

from insights import price_move_insights
from model_ids import overlaps_used
from screens.setup import render_connect_account
from session_data import (
    load_ref_price_changes,
    load_snapshot,
    load_usage_by_model,
    mode_banner,
)
from theme import hero, recommendation_card


def render() -> None:
    hero(
        "Price Watch",
        "Public LLM list-price moves overlaid on models in your Cortex usage — "
        "competitive context Snowsight cost charts do not provide.",
        kicker="Prices",
    )

    days = int(st.session_state.get("days", 90))
    credit_price = float(st.session_state.get("credit_price_usd", 3.0))
    usage, mode = load_usage_by_model(days)
    mode_banner(mode)

    used_models: set[str] = set()
    if not usage.empty:
        used_models = {str(m) for m in usage["MODEL_NAME"].dropna().unique()}

    changes = load_ref_price_changes()
    if not changes.empty:
        st.caption("Change feed from bound Marketplace dataset.")
        changes = changes.copy()
        changes["FLAGGED_IN_USE"] = changes["MODEL_ID"].astype(str).apply(
            lambda mid: overlaps_used(str(mid), used_models)
        )
        flagged = changes[changes["FLAGGED_IN_USE"] == True]  # noqa: E712
        st.subheader("Moves affecting models you use")
        if flagged.empty:
            st.caption("No overlap with your usage in this window — full feed below.")
        else:
            st.dataframe(flagged, use_container_width=True)
        st.subheader("All bound changes")
        st.dataframe(changes, use_container_width=True)
        render_connect_account()
        return

    snap = load_snapshot()
    llm = snap[snap["row_type"] == "llm"].copy()
    top = price_move_insights(usage, llm, credit_price, limit=5)
    all_hits = price_move_insights(usage, llm, credit_price, limit=None)
    for insight in top:
        recommendation_card(insight)
    if len(all_hits) > 5:
        with st.expander(f"All overlapping price moves ({len(all_hits)})"):
            for insight in all_hits[5:]:
                recommendation_card(insight)

    moved = llm[llm["change_pct_90d"].fillna(0) != 0]
    st.caption("Bundled snapshot flags (bind Marketplace view for accumulating SCD2 history).")
    if moved.empty:
        st.dataframe(llm, use_container_width=True)
        render_connect_account()
        return

    moved = moved.copy()
    moved["FLAGGED_IN_USE"] = moved["model_name"].astype(str).apply(
        lambda name: overlaps_used(name, used_models)
    )
    st.dataframe(moved.sort_values("change_pct_90d"), use_container_width=True)
    if not used_models:
        st.caption("Connect live usage to flag moves against models you actually call.")
    render_connect_account()
