"""About / Trust — credibility, security matrix, changelog pointer."""

from __future__ import annotations

import streamlit as st

from session_data import APP_VERSION


def render() -> None:
    st.title("About / Trust")
    st.caption(f"Cortex Cost Advisor v{APP_VERSION} · Free · Read-only Native App")

    st.markdown(
        """
## Who built this

Independent open-source project by **Digvijay Vaghela**.  
Repository (un-obfuscated source): https://github.com/dgvj-work/ai-price-intelligence  
Support email: **digvijay.vaghela@yahoo.com** (best-effort response; no paid SLA in v1)

**Update cadence:** App patches as needed; optional Marketplace price dataset refreshes **weekly**.  
**Changelog:** see `CHANGELOG.md` in the application package / GitHub repo.

## Why this app exists

Snowflake already offers cost management, budgets, and resource monitors. Those tools
answer “how many credits did the account burn?”  

Cortex Cost Advisor answers:

1. **Which Cortex functions/models** drove spend?
2. **What if** the same tokens ran on a cheaper Cortex model? (**Model Advisor**)
3. **Did public list prices move** on models we care about? (**Price Watch**)

## Security & permissions (read before granting)

### Required privilege

`GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO APPLICATION CORTEX_COST_ADVISOR;`

| Question | Answer |
|----------|--------|
| What is read? | `ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY` (preferred) or `CORTEX_AISQL_USAGE_HISTORY`; AI/Cortex-related rows from `METERING_HISTORY` |
| Query window | Last **90 days** only |
| QUERY_HISTORY / SQL text? | **Never** |
| Customer tables? | **Never** (unless you optionally bind Marketplace price views) |
| Data leaving Snowflake? | **No** — no network access, external functions, external access integrations, SPCS, or telemetry |
| Writes? | Only objects inside the application’s own schemas |
| Why whole SNOWFLAKE DB privilege? | Snowflake Native Apps do not support granting a single ACCOUNT_USAGE view to an app; this privilege is the documented, auditable mechanism |

### Optional references

Bind views from **AI Model & Compute Price Intelligence** for live weekly prices.
Without bindings, Model Advisor / Price Watch use a **bundled CSV snapshot** — the app
works standalone.

### Preview mode

Until the privilege is granted (or if Cortex has produced no rows yet), Overview /
Model Advisor / Price Watch show **labeled sample data** so you can evaluate UX and
value before approving account-level access. Sample data is never billed usage.

## What never happens

- No egress from your Snowflake account  
- No obfuscated application code  
- No unbounded history scans  

## Support expectations

Email support for install, privilege, and data-binding questions. This free listing
does not include a contractual uptime SLA.
        """
    )
