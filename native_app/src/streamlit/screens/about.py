"""Trust - buyer, moat, security, and honest limitations."""

from __future__ import annotations

import streamlit as st

from session_data import APP_VERSION, SUPPORT_EMAIL, SUPPORT_URL
from theme import hero


def render() -> None:
    hero(
        "Trust & product intent",
        "Why grant imported privileges, and what unique decision this app supports.",
        kicker=f"Trust | v{APP_VERSION}",
    )

    st.markdown(
        f"""
## The three questions (answered)

### 1. Unique value vs raw SQL / Snowsight?

Snowsight answers "how many credits did we burn?"  
This app answers:

- **Which Cortex model should we migrate off** to cut spend (ranked switch savings)?
- **Is spend dangerously concentrated** on one model?
- **Which days spiked** vs your own median?
- **What is a simple forward planning number** for the next 30 days?
- **Did public list prices move** on models overlapping your usage?

That recommendation pack is the product. Credit charts are evidence.

### 2. Who is the buyer, and what decision?

**Buyer:** FinOps lead or platform engineer owning Snowflake Cortex costs.  
**Decision:** allow-list / migrate Cortex models and challenge AI spend without reading `QUERY_HISTORY`.

### 3. Why trust a Marketplace app with `IMPORTED PRIVILEGES`?

| Control | Detail |
|---------|--------|
| Privilege | `IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE` (Native Apps cannot take a single-view grant) |
| Reads | `CORTEX_AI_FUNCTIONS_USAGE_HISTORY` or `CORTEX_AISQL_USAGE_HISTORY`; AI/Cortex rows in `METERING_HISTORY` |
| Window | Up to **365 days** (UI selectable) |
| Never | `QUERY_HISTORY`, SQL text, network egress, SPCS, telemetry |
| Writes | App schema only |
| Code | Un-obfuscated on GitHub |
| Preview | Evaluate recommendations on sample data **before** granting |

New teammates: open the sidebar tab **Getting started** for the setup walkthrough.

Publisher: **Digvijay Vaghela**  
Support: [GitHub Discussions]({SUPPORT_URL})  
Email: {SUPPORT_EMAIL}  
Repo: https://github.com/dgvj-work/ai-price-intelligence  
SLA: best-effort community support (free listing; no contractual uptime SLA in v{APP_VERSION})

This app does not phone home. After the Marketplace listing is published, the publisher
sees install/usage analytics in Snowflake **Provider Studio** (company and account when
Snowflake provides them), not from fields typed inside the app.

## Architecture (no manual "refresh product")

Passthrough views over ACCOUNT_USAGE are created when privileges exist and rebound
**silently on session start**. We intentionally do **not** require `EXECUTE TASK`
to materialize history, because that would expand the privilege surface. Streamlit caches
query results briefly; reopen the app after new Cortex activity (ACCOUNT_USAGE lag ~45m).

## Honest limitations

- Switch savings use **list Cortex credit rates**, not your negotiated quality constraints.
- USD requires **your** $/credit. Snowflake does not expose contracted rates to apps.
- Not a substitute for Snowflake budgets / resource monitors for account-wide FinOps.
- Forward estimate is trailing-average math, not a trained forecast model.

## Changelog

See `CHANGELOG.md` in the application package (v{APP_VERSION}).
        """
    )
