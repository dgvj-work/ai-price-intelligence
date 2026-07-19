"""UI helpers using only Streamlit native widgets (no unsafe_allow_html / CSS inject).

Brand colors live in `.streamlit/config.toml` (primary teal / cool neutrals).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import streamlit as st

BRAND = "Cortex Cost Advisor"


def apply_theme() -> None:
    """Theme is applied via `.streamlit/config.toml` at runtime."""
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


def hero(title: str, subtitle: str, kicker: str | None = None) -> None:
    """Page header with brand-first kicker and calm hierarchy."""
    brand_line = (kicker or BRAND).strip().upper()
    with panel(border=True):
        st.caption(brand_line)
        st.title(title)
        if subtitle:
            st.markdown(subtitle)


def section(title: str, subtitle: str | None = None) -> None:
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)


def recommendation_card(insight, *, lead: bool = False) -> None:
    sev = insight.severity if insight.severity in ("high", "medium", "info") else "info"
    tag = "Primary recommendation" if lead else insight.kind.replace("_", " ").title()
    sev_label = {"high": "High impact", "medium": "Worth review", "info": "Context"}[sev]

    meta_bits: list[str] = []
    if getattr(insight, "savings_credits", None) is not None:
        meta_bits.append(f"~{insight.savings_credits:,.2f} credits")
    if getattr(insight, "savings_usd", None) is not None:
        meta_bits.append(f"~${insight.savings_usd:,.0f} est.")
    meta = (" | ".join(meta_bits) + "\n\n") if meta_bits else ""

    body = (
        f"**{tag}**  ·  {sev_label}\n\n"
        f"**{insight.headline}**\n\n"
        f"{insight.detail}"
    )
    # Prefer ASCII separator (avoid middle-dot AI tell)
    body = body.replace("  ·  ", " | ")
    if meta_bits:
        body = f"{body}\n\n{meta.strip()}"

    # Severity color via native Streamlit alerts (theme primary tints widgets).
    if sev == "high" or lead:
        st.success(body)
    elif sev == "medium":
        st.warning(body)
    else:
        st.info(body)


def metric_strip(items: list[tuple[str, str, str | None]]) -> None:
    """items: (label, value, optional help)."""
    with panel(border=True):
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
