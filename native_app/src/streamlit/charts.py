"""Branded Altair charts (no HTML). Falls back to Streamlit charts if Altair missing."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

TEAL = "#0f766e"
TEAL_SOFT = "#99f6e4"
AMBER = "#d97706"
ROSE = "#e11d48"
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


def sparkline(series: pd.Series, *, height: int = 56) -> None:
    """Tiny trend line for metric strips."""
    if series is None or len(series.dropna()) < 2:
        return
    frame = pd.DataFrame({"i": range(len(series)), "v": series.astype(float).values})
    alt = _altair()
    if alt is None:
        st.line_chart(frame.set_index("i")["v"], height=height)
        return
    chart = (
        alt.Chart(frame)
        .mark_area(line={"color": TEAL}, color=TEAL_SOFT, opacity=0.5)
        .encode(
            x=alt.X("i:Q", axis=None),
            y=alt.Y("v:Q", axis=None),
            tooltip=[alt.Tooltip("v:Q", title="Value", format=",.2f")],
        )
        .properties(height=height)
        .configure_view(strokeWidth=0)
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


def price_change_bars(frame: pd.DataFrame, *, label_col: str, pct_col: str) -> None:
    """Diverging bars for 90d list-price % moves (snapshot path)."""
    if frame is None or frame.empty:
        return
    data = frame[[label_col, pct_col]].dropna().copy()
    data = data[data[pct_col].astype(float) != 0]
    if data.empty:
        st.caption("No non-zero 90-day list-price moves in this feed.")
        return
    data["label"] = data[label_col].astype(str)
    data["pct"] = data[pct_col].astype(float)
    data["direction"] = data["pct"].apply(lambda p: "down" if p < 0 else "up")

    alt = _altair()
    if alt is None:
        st.bar_chart(data.set_index("label")["pct"])
        return

    chart = (
        alt.Chart(data)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            x=alt.X("pct:Q", title="90d list-price change %", axis=alt.Axis(labelColor=MUTED, gridColor=GRID)),
            y=alt.Y("label:N", sort="-x", title=None, axis=alt.Axis(labelColor=SLATE)),
            color=alt.Color(
                "direction:N",
                scale=alt.Scale(domain=["down", "up"], range=[TEAL, ROSE]),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("label:N", title="Model"),
                alt.Tooltip("pct:Q", title="Change %", format="+.1f"),
            ],
        )
        .properties(height=max(180, 32 * len(data)))
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(chart, use_container_width=True)


def price_change_timeline(frame: pd.DataFrame) -> None:
    """Timeline of bound Marketplace price-change events."""
    if frame is None or frame.empty:
        return
    cols = {c.upper(): c for c in frame.columns}
    ts_col = cols.get("CHANGED_AT")
    model_col = cols.get("MODEL_ID") or cols.get("MODEL_NAME")
    pct_col = cols.get("INPUT_PCT_CHANGE") or cols.get("OUTPUT_PCT_CHANGE")
    if not ts_col or not model_col or not pct_col:
        return

    data = frame[[ts_col, model_col, pct_col]].dropna().copy()
    if data.empty:
        return
    data = data.rename(columns={ts_col: "when", model_col: "model", pct_col: "pct"})
    data["when"] = pd.to_datetime(data["when"], errors="coerce")
    data = data.dropna(subset=["when"])
    if data.empty:
        return

    alt = _altair()
    if alt is None:
        st.scatter_chart(data, x="when", y="pct")
        return

    chart = (
        alt.Chart(data)
        .mark_circle(size=80, opacity=0.85)
        .encode(
            x=alt.X("when:T", title=None, axis=alt.Axis(labelColor=MUTED, tickColor=GRID)),
            y=alt.Y("pct:Q", title="List-price change %", axis=alt.Axis(labelColor=MUTED, gridColor=GRID)),
            color=alt.condition(
                alt.datum.pct < 0,
                alt.value(TEAL),
                alt.value(AMBER),
            ),
            tooltip=[
                alt.Tooltip("when:T", title="When"),
                alt.Tooltip("model:N", title="Model"),
                alt.Tooltip("pct:Q", title="Change %", format="+.1f"),
            ],
        )
        .properties(height=260)
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(chart, use_container_width=True)
