"""Model Advisor — switch scenarios using dataset reference or bundled snapshot."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from session_data import (
    empty_state,
    load_ref_cortex_current,
    load_snapshot,
    load_usage_by_model,
)


def render() -> None:
    st.title("Model Advisor")
    st.caption(
        "Answer: “If the same tokens had run on another Cortex model, what would "
        "credits look like?” Uses your ACCOUNT_USAGE volumes × list rates "
        "(live dataset when bound, otherwise bundled snapshot)."
    )

    days = int(st.session_state.get("days", 90))
    credit_price = float(st.session_state.get("credit_price_usd", 3.0))
    usage = load_usage_by_model(days)

    cortex_prices = load_ref_cortex_current()
    using_dataset = not cortex_prices.empty

    if not using_dataset:
        snap = load_snapshot()
        cortex_prices = snap[snap["row_type"] == "cortex"].copy()
        if not cortex_prices.empty:
            cortex_prices = cortex_prices.rename(
                columns={
                    "cortex_function": "FUNCTION_NAME",
                    "cortex_model": "MODEL_NAME",
                    "credits_per_1m_tokens": "CREDITS_PER_1M_TOKENS",
                }
            )
        st.info(
            "Dataset reference `price_intel_cortex_current` is not bound. "
            "Using the bundled price snapshot. For live weekly rates, mount "
            "**AI Model & Compute Price Intelligence** and bind "
            "`SHARE.VW_CORTEX_CURRENT` in the app’s references."
        )
    else:
        st.success("Using bound Marketplace dataset reference `price_intel_cortex_current`.")

    if usage.empty:
        empty_state(
            "No Cortex function usage in this window, so there is nothing to advise on yet."
        )
        if not cortex_prices.empty:
            st.subheader("Available Cortex list rates")
            st.dataframe(cortex_prices, use_container_width=True)
        return

    st.subheader("Your usage")
    usage = usage.copy()
    usage["USD_EST"] = usage["CREDITS"] * credit_price
    st.dataframe(usage, use_container_width=True)

    st.subheader("Switch scenarios")
    st.write(
        "For each model you used, estimate credits if the **same token volume** ran on "
        "another Cortex model (list rates from "
        + ("live dataset" if using_dataset else "bundled snapshot")
        + ")."
    )

    if cortex_prices.empty:
        empty_state("No Cortex price table available.")
        return

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
        empty_state("Could not build scenarios.")
        return
    scen = pd.DataFrame(rows)
    scen = scen[scen["YOUR_MODEL"].str.lower() != scen["ALT_MODEL"].str.lower()]
    st.dataframe(scen.sort_values("USD_DELTA"), use_container_width=True)
