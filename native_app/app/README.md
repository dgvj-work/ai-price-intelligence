# Cortex Cost Advisor (v1.0.0)

A **free, read-only** Snowflake Native App that helps you understand Cortex / AI SQL spend and compare model pricing scenarios.

## Quick setup after install

1. As `ACCOUNTADMIN`, grant imported privileges (Snowsight → app **Privileges**, or SQL):

```sql
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO APPLICATION CORTEX_COST_ADVISOR;
```

2. Open the app → **Overview** → click **Configure** (or **Refresh usage data** in the sidebar).
3. ACCOUNT_USAGE can lag live Cortex activity by up to ~45 minutes.

## What this app reads

With **Imported Privileges on the SNOWFLAKE database**, the app reads:

- `SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY` (preferred)
- or `SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AISQL_USAGE_HISTORY` (fallback)
- AI/Cortex-related rows from `SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY` (last 90 days)

It does **not** read `QUERY_HISTORY` or any query text.

Snowflake Native Apps expose ACCOUNT_USAGE via this privilege only — there is no supported per-view grant to an application.

### Optional Marketplace dataset

Bind these references (Snowsight → app privileges / references) to the **AI Model & Compute Price Intelligence** listing for live prices:

- `price_intel_model_current` → `…SHARE.VW_MODEL_CURRENT`
- `price_intel_cortex_current` → `…SHARE.VW_CORTEX_CURRENT`
- `price_intel_price_changes` → `…SHARE.VW_PRICE_CHANGES_90D`

If unbound, Model Advisor / Price Watch use a bundled CSV snapshot so the app still works standalone.

## Pages

| Page | Purpose |
|------|---------|
| Overview | Credits, USD estimate, trend, top functions |
| Model Advisor | Switch-cost scenarios for models you used |
| Price Watch | List-price moves flagged against your usage |
| About / Trust | Permissions, latency, and privacy posture |

## What this app never does

- No writes outside the application’s own schema
- No external access integrations, external functions, or network calls
- No Snowpark Container Services
- No telemetry or data leaving your Snowflake account
- No unbounded history scans (queries capped at 90 days)

## Trust

All application code is un-obfuscated and inspectable.  
Source: https://github.com/dgvj-work/ai-price-intelligence  
Support: digvijay.vaghela@yahoo.com
