"""Branded Altair charts (no HTML). Falls back to Streamlit charts if Altair missing."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

TEAL = "#0f766e"
TEAL_SOFT = "#99f6e4"
MUTED = "#64748b"
SLATE = "#0f172a"
GRID = "#e2e8f0"


def _altair():
    try:
        import altair as alt

        return alt
    except Exception:  # noqa: BLE001
        return None


def spend_trend_chart(daily: pd.DataFrame, *, x: str = "DAY", y: str = "CREDITS") -> None:
    """Daily Cortex credit trend with brand colors."""
    if daily is None or daily.empty:
        st.caption("No trend data in this window.")
        return

    frame = daily[[x, y]].dropna().copy()
    if frame.empty:
        st.caption("No trend data in this window.")
        return

    alt = _altair()
    if alt is None:
        st.line_chart(frame, x=x, y=y)
        return

    base = alt.Chart(frame).encode(
        x=alt.X(f"{x}:T", title=None, axis=alt.Axis(labelColor=MUTED, tickColor=GRID)),
        y=alt.Y(f"{y}:Q", title="Credits", axis=alt.Axis(labelColor=MUTED, gridColor=GRID)),
        tooltip=[
            alt.Tooltip(f"{x}:T", title="Day"),
            alt.Tooltip(f"{y}:Q", title="Credits", format=",.2f"),
        ],
    )
    area = base.mark_area(color=TEAL_SOFT, opacity=0.45)
    line = base.mark_line(color=TEAL, strokeWidth=2.5)
    points = base.mark_circle(color=TEAL, size=35)
    chart = (
        (area + line + points)
        .properties(height=280)
        .configure_view(strokeWidth=0)
        .configure_axis(domainColor=GRID)
    )
    st.altair_chart(chart, use_container_width=True)


def switch_savings_bars(rows: list[dict[str, Any]]) -> None:
    """Horizontal bars for top switch USD savings."""
    if not rows:
        return
    frame = pd.DataFrame(rows)
    if frame.empty or "usd" not in frame.columns:
        return

    alt = _altair()
    if alt is None:
        st.bar_chart(frame.set_index("label")["usd"])
        return

    chart = (
        alt.Chart(frame)
        .mark_bar(cornerRadiusEnd=3, color=TEAL)
        .encode(
            x=alt.X("usd:Q", title="Est. USD savings", axis=alt.Axis(labelColor=MUTED, gridColor=GRID)),
            y=alt.Y("label:N", sort="-x", title=None, axis=alt.Axis(labelColor=SLATE)),
            tooltip=[
                alt.Tooltip("label:N", title="Switch"),
                alt.Tooltip("usd:Q", title="USD est.", format="$,.0f"),
                alt.Tooltip("credits:Q", title="Credits", format=",.2f"),
            ],
        )
        .properties(height=max(160, 36 * len(frame)))
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(chart, use_container_width=True)
