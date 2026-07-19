"""Price Watch — list-price moves flagged against models you use (live or preview)."""

from __future__ import annotations

import streamlit as st

from screens.setup import render_connect_account
from session_data import (
    load_ref_price_changes,
    load_snapshot,
    load_usage_by_model,
    mode_banner,
)


def render() -> None:
    st.title("Price Watch")
    st.markdown(
        """
**Differentiator vs Snowsight:** overlay **public LLM list-price moves** on the models
your account actually called — not a generic credit chart.
        """
    )

    days = int(st.session_state.get("days", 90))
    usage, mode = load_usage_by_model(days)
    mode_banner(mode)

    used_models: set[str] = set()
    if not usage.empty:
        used_models = {str(m).lower() for m in usage["MODEL_NAME"].dropna().unique()}

    changes = load_ref_price_changes()
    if not changes.empty:
        st.caption("Change feed from your bound Marketplace price dataset.")
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
            st.info(
                "No recent list-price changes overlap your Cortex models in this window. "
                "Full feed below."
            )
        else:
            st.dataframe(flagged, use_container_width=True)
        st.subheader("All bound changes (90d)")
        st.dataframe(changes, use_container_width=True)
        render_connect_account()
        return

    snap = load_snapshot()
    llm = snap[snap["row_type"] == "llm"].copy()
    moved = llm[llm["change_pct_90d"].fillna(0) != 0]
    st.caption(
        "Change flags from the bundled price snapshot. Bind the Marketplace "
        "90-day price-changes view for full SCD2 history as it accumulates weekly."
    )

    if moved.empty:
        st.info(
            "No non-zero 90-day change flags in the bundled snapshot yet. "
            "Showing current list prices so you can still explore the page."
        )
        st.dataframe(llm, use_container_width=True)
        render_connect_account()
        return

    moved = moved.copy()
    # Preview usage is Cortex-centric; also flag well-known public models in snapshot.
    moved["FLAGGED_IN_USE"] = moved["model_name"].astype(str).str.lower().apply(
        lambda name: any(m in name or name in m for m in used_models)
        or any(k in name for k in ("claude", "gpt-4o", "deepseek", "gemini"))
    )
    st.subheader("Notable list-price moves")
    st.dataframe(moved.sort_values("change_pct_90d"), use_container_width=True)
    st.caption(
        "FLAGGED_IN_USE highlights overlap with your usage window "
        + ("(preview sample models)" if mode == "preview" else "(live Cortex models)")
        + "."
    )

    render_connect_account()
