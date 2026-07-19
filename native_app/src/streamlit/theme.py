"""UI helpers using only Streamlit native widgets - no unsafe_allow_html / CSS inject."""

from __future__ import annotations

import streamlit as st


def apply_theme() -> None:
    """No-op kept for call-site compatibility. Avoids HTML/CSS injection for review."""
    return


def hero(title: str, subtitle: str, kicker: str = "Cortex Cost Advisor") -> None:
    st.caption(kicker)
    st.title(title)
    st.write(subtitle)
    st.divider()


def recommendation_card(insight, *, lead: bool = False) -> None:
    sev = insight.severity if insight.severity in ("high", "medium", "info") else "info"
    tag = "Primary recommendation" if lead else insight.kind.replace("_", " ").title()
    header = f"**{tag}**: {insight.headline}"
    body = insight.detail
    if sev == "high":
        st.success(f"{header}\n\n{body}")
    elif sev == "medium":
        st.info(f"{header}\n\n{body}")
    else:
        st.markdown(f"{header}\n\n{body}")
