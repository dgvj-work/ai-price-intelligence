"""About / Trust — plain-language privacy posture and permissions."""

from __future__ import annotations

import streamlit as st


def render() -> None:
    st.title("About / Trust")
    st.caption("Cortex Cost Advisor v1.0.0 — free, read-only Native App.")

    st.markdown(
        """
## What you get

| Page | Purpose |
|------|---------|
| **Overview** | Cortex / AI credits, USD estimate, spend trend, top functions |
| **Model Advisor** | Switch scenarios: same tokens on alternate Cortex model rates |
| **Price Watch** | Recent list-price moves, flagged when they overlap your usage |
| **About / Trust** | This page — permissions, latency, and what never happens |

## Security & permissions

### Required privilege

**Imported privileges on the SNOWFLAKE database**

Snowflake Native Apps use this privilege to read ACCOUNT_USAGE metering inside
the consumer account. There is no supported way to grant a single ACCOUNT_USAGE
view to an application.

**Why we ask for it**

- Show *your* Cortex / AI spend (not sample data)
- Build Model Advisor scenarios from models you actually called
- Highlight Price Watch rows that match your usage

**What is read (after grant)**

- `CORTEX_AI_FUNCTIONS_USAGE_HISTORY` (preferred) or `CORTEX_AISQL_USAGE_HISTORY`
- AI / Cortex-related rows from `METERING_HISTORY` (last 90 days)

**What is never read**

- `QUERY_HISTORY` or any SQL text
- Customer tables outside the app (unless you optionally bind Marketplace price views)

### Optional dataset references

Bind views from **AI Model & Compute Price Intelligence** for live weekly prices.
Without bindings, Model Advisor / Price Watch use a bundled CSV snapshot — the app
still works standalone.

### Data freshness

ACCOUNT_USAGE can lag live activity by up to **~45 minutes**. App queries are capped
at **90 days**. Price snapshot / Marketplace dataset refresh is **weekly**.

## What never happens

- Nothing leaves your Snowflake account (no network calls, external access
  integrations, external functions, containers, or telemetry)
- No writes outside the application’s own schema
- Application code is **un-obfuscated** and inspectable for security review

## Source & support

Public repository: https://github.com/dgvj-work/ai-price-intelligence  

Support: digvijay.vaghela@yahoo.com
        """
    )
