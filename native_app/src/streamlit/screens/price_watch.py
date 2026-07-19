"""Price Watch — recent price changes affecting models you use."""

from __future__ import annotations

import streamlit as st

from session_data import (
    empty_state,
    load_ref_price_changes,
    load_snapshot,
    load_usage_by_model,
)


def render() -> None:
    st.title("Price Watch")
    st.caption("Recent list-price moves, highlighted when they match your usage.")

    days = int(st.session_state.get("days", 90))
    usage = load_usage_by_model(days)
    used_models: set[str] = set()
    if not usage.empty:
        used_models = {str(m).lower() for m in usage["MODEL_NAME"].dropna().unique()}

    changes = load_ref_price_changes()
    if not changes.empty:
        st.success("Using bound Marketplace dataset reference `price_intel_price_changes`.")
        changes = changes.copy()
        changes["FLAGGED_IN_USE"] = (
            changes["MODEL_ID"].astype(str).str.lower().apply(
                lambda mid: any(m in mid for m in used_models)
            )
            if used_models
            else False
        )
        flagged = changes[changes["FLAGGED_IN_USE"] == True]  # noqa: E712
        st.subheader("Changes affecting models you use")
        if flagged.empty:
            empty_state(
                "No recent list-price changes overlap your Cortex models in this window."
            )
        else:
            st.dataframe(flagged, use_container_width=True)
        st.subheader("All bound changes (90d)")
        st.dataframe(changes, use_container_width=True)
        return

    snap = load_snapshot()
    llm = snap[snap["row_type"] == "llm"].copy()
    moved = llm[llm["change_pct_90d"].fillna(0) != 0]
    st.info(
        "Dataset reference `price_intel_price_changes` is not bound. "
        "Showing bundled snapshot flags. Bind `SHARE.VW_PRICE_CHANGES_90D` for full "
        "SCD2 history (history accumulates weekly from your first dataset publish)."
    )
    if moved.empty:
        empty_state(
            "No non-zero change flags in the bundled snapshot yet. "
            "After the dataset has run for a few weeks, bind the Marketplace view for real diffs."
        )
        st.dataframe(llm, use_container_width=True)
        return
    moved = moved.copy()
    moved["FLAGGED_IN_USE"] = moved["model_name"].astype(str).str.lower().isin(used_models)
    st.dataframe(moved.sort_values("change_pct_90d"), use_container_width=True)
