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


def brand_header(*, compact: bool = False) -> None:
    """Sidebar brand mark + name.

    SiS Native Apps often break st.image (stage paths / BytesIO). Use a text
    monogram that always renders; keep PNG assets for listing screenshots only.
    """
    st.markdown(f"### ◈  {BRAND}")
    if not compact:
        st.caption("FinOps recommendations for Cortex")


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
    """
    Primary: full bordered panel + savings metrics (distinct from Streamlit alerts).
    Secondary: compact bordered panel with severity caption only.
    """
    sev = insight.severity if insight.severity in ("high", "medium", "info") else "info"
    tag = "Primary recommendation" if lead else insight.kind.replace("_", " ").title()
    sev_label = {"high": "High impact", "medium": "Worth review", "info": "Context"}[sev]

    credits = getattr(insight, "savings_credits", None)
    usd = getattr(insight, "savings_usd", None)

    if lead:
        with panel(border=True):
            st.caption(f"{tag}  |  {sev_label}")
            st.markdown(f"### {insight.headline}")
            st.write(insight.detail)
            if credits is not None or usd is not None:
                m1, m2 = st.columns(2)
                if credits is not None:
                    m1.metric("Credits you could save", f"{credits:,.2f}")
                if usd is not None:
                    m2.metric("USD estimate", f"${usd:,.0f}")
            st.caption("List-rate scenario. Validate quality before changing production models.")
        return

    # Secondary: quieter, no alert chrome
    with panel(border=True):
        st.caption(f"{tag}  |  {sev_label}")
        st.markdown(f"**{insight.headline}**")
        st.caption(insight.detail)
        bits: list[str] = []
        if credits is not None:
            bits.append(f"~{credits:,.2f} credits")
        if usd is not None:
            bits.append(f"~${usd:,.0f} est.")
        if bits:
            st.caption(" | ".join(bits))


def metric_strip(
    items: list[tuple[str, str, str | None]],
    *,
    spark=None,
) -> None:
    """items: (label, value, optional help). Optional spark = pandas Series for mini trend."""
    with panel(border=True):
        cols = st.columns(len(items))
        for col, (label, value, help_text) in zip(cols, items):
            kwargs = {"help": help_text} if help_text else {}
            col.metric(label, value, **kwargs)
        if spark is not None:
            try:
                from charts import sparkline

                st.caption("Credit trend in this window")
                sparkline(spark)
            except Exception:  # noqa: BLE001
                pass


def table(df, **kwargs) -> None:
    """Dataframe with quiet defaults; tolerate older Streamlit builds."""
    opts = {"use_container_width": True, "hide_index": True}
    opts.update(kwargs)
    try:
        st.dataframe(df, **opts)
    except TypeError:
        opts.pop("hide_index", None)
        st.dataframe(df, **opts)
