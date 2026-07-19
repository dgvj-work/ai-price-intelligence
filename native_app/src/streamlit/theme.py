"""Lightweight brand styling — FinOps product, not default Streamlit tutorial look."""

from __future__ import annotations

import streamlit as st

CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500&display=swap');

  html, body, [class*="css"] {
    font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
  }

  .cca-hero {
    background: linear-gradient(135deg, #0b1f2a 0%, #123a4a 55%, #1a5c5c 100%);
    color: #f4f7f8;
    padding: 1.4rem 1.6rem;
    border-radius: 0;
    margin-bottom: 1.1rem;
    border-left: 4px solid #3ecf8e;
  }
  .cca-hero h1 {
    font-size: 1.55rem;
    font-weight: 700;
    margin: 0 0 0.35rem 0;
    letter-spacing: -0.02em;
    color: #fff !important;
  }
  .cca-hero p {
    margin: 0;
    opacity: 0.92;
    font-size: 0.98rem;
    line-height: 1.45;
    max-width: 52rem;
  }
  .cca-kicker {
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #3ecf8e;
    margin-bottom: 0.35rem;
  }

  .cca-rec {
    border: 1px solid #d5e0e6;
    background: #f7fbf9;
    padding: 1.1rem 1.25rem;
    margin: 0.6rem 0 1rem 0;
    border-left: 4px solid #0f766e;
  }
  .cca-rec.high { border-left-color: #b45309; background: #fffbeb; }
  .cca-rec.medium { border-left-color: #0f766e; }
  .cca-rec.info { border-left-color: #475569; background: #f8fafc; }
  .cca-rec h3 {
    margin: 0 0 0.4rem 0;
    font-size: 1.15rem;
    font-weight: 650;
    color: #0f172a;
  }
  .cca-rec p { margin: 0; color: #334155; font-size: 0.95rem; line-height: 1.45; }
  .cca-tag {
    display: inline-block;
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.68rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    background: #0f172a;
    color: #e2e8f0;
    padding: 0.15rem 0.45rem;
    margin-bottom: 0.45rem;
  }

  .cca-muted { color: #64748b; font-size: 0.85rem; }
  div[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f4f7f8 0%, #eef3f5 100%);
  }
</style>
"""


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str, kicker: str = "Cortex Cost Advisor") -> None:
    st.markdown(
        f"""
<div class="cca-hero">
  <div class="cca-kicker">{kicker}</div>
  <h1>{title}</h1>
  <p>{subtitle}</p>
</div>
        """,
        unsafe_allow_html=True,
    )


def recommendation_card(insight, *, lead: bool = False) -> None:
    sev = insight.severity if insight.severity in ("high", "medium", "info") else "info"
    tag = "Primary recommendation" if lead else insight.kind.replace("_", " ")
    st.markdown(
        f"""
<div class="cca-rec {sev}">
  <div class="cca-tag">{tag}</div>
  <h3>{insight.headline}</h3>
  <p>{insight.detail}</p>
</div>
        """,
        unsafe_allow_html=True,
    )
