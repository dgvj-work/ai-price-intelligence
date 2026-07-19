"""About / Trust — plain-language privacy posture."""

from __future__ import annotations

import streamlit as st


def render() -> None:
    st.title("About / Trust")
    st.markdown(
        """
## What Cortex Cost Advisor reads

With **Imported Privileges on the SNOWFLAKE database**, this app reads:

- `CORTEX_AI_FUNCTIONS_USAGE_HISTORY` (preferred) or `CORTEX_AISQL_USAGE_HISTORY` (fallback)
- AI/Cortex-related rows from `METERING_HISTORY` (last 90 days)

It does **not** read `QUERY_HISTORY` or any SQL text.

Optional: bind Marketplace dataset references for live model / Cortex prices and 90-day
change history. Without bindings, a bundled CSV snapshot ships in the app package.

## What never happens

- Nothing leaves your Snowflake account (no network calls, no external access integrations,
  no external functions, no containers, no telemetry).
- The app is **read-only** with respect to your data: it does not write outside its own
  application schema.
- Queries are capped at **90 days**.
- Application code is **un-obfuscated** and inspectable for Snowflake security review.

## Source

Public repository (replace with your GitHub URL before publish):
`https://github.com/YOUR_ORG/ai-price-intelligence`
        """
    )
