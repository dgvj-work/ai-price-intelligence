"""UI helpers using only Streamlit native widgets (no unsafe_allow_html / CSS inject)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import streamlit as st


def apply_theme() -> None:
    """No-op kept for call-site compatibility. Avoids HTML/CSS injection for review."""
    return


@contextmanager
def panel(*, border: bool = True) -> Iterator[None]:
    """Soft visual grouping. Falls back if this Streamlit build lacks bordered containers."""
    try:
        with st.container(border=border):
            yield
    except TypeError:
        with st.container():
            yield


def hero(title: str, subtitle: str, kicker: str = "Cortex Cost Advisor") -> None:
    st.caption(kicker)
    st.title(title)
    if subtitle:
        st.markdown(subtitle)
    st.divider()


def section(title: str, subtitle: str | None = None) -> None:
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)


def recommendation_card(insight, *, lead: bool = False) -> None:
    sev = insight.severity if insight.severity in ("high", "medium", "info") else "info"
    tag = "Primary recommendation" if lead else insight.kind.replace("_", " ").title()
    sev_label = {"high": "High impact", "medium": "Worth review", "info": "Context"}[sev]

    with panel(border=True):
        st.caption(f"{tag}  |  {sev_label}")
        st.markdown(f"**{insight.headline}**")
        st.write(insight.detail)
        meta_bits: list[str] = []
        if getattr(insight, "savings_credits", None) is not None:
            meta_bits.append(f"~{insight.savings_credits:,.2f} credits")
        if getattr(insight, "savings_usd", None) is not None:
            meta_bits.append(f"~${insight.savings_usd:,.0f} est.")
        if meta_bits:
            st.caption(" | ".join(meta_bits))


def metric_strip(items: list[tuple[str, str, str | None]]) -> None:
    """items: (label, value, optional help)."""
    cols = st.columns(len(items))
    for col, (label, value, help_text) in zip(cols, items):
        kwargs = {"help": help_text} if help_text else {}
        col.metric(label, value, **kwargs)


def table(df, **kwargs) -> None:
    """Dataframe with quiet defaults; tolerate older Streamlit builds."""
    opts = {"use_container_width": True, "hide_index": True}
    opts.update(kwargs)
    try:
        st.dataframe(df, **opts)
    except TypeError:
        opts.pop("hide_index", None)
        st.dataframe(df, **opts)
