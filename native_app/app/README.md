# Cortex Cost Advisor (v1.0.1)

A **free, read-only** Snowflake Native App for **Cortex / AI FinOps** — model-level spend, switch scenarios, and public list-price watch — with **zero data egress**.

## First open (no admin grant yet)

The app opens in **Preview mode** with labeled sample Cortex charts so you can evaluate Overview, Model Advisor, and Price Watch immediately. Sample data is not your billed usage.

## Connect live usage (one admin step)

1. As `ACCOUNTADMIN`:

```sql
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO APPLICATION CORTEX_COST_ADVISOR;
```

Or: Snowsight → app → **Privileges** → grant Imported privileges on SNOWFLAKE.

2. Open the app (views refresh automatically) or click **Connect live usage** on Overview.

ACCOUNT_USAGE can lag live Cortex activity by up to ~45 minutes.

## Why not only Snowsight?

| Native Snowsight cost tools | This app |
|-----------------------------|----------|
| Account / warehouse credit rollups, budgets | Cortex **function + model** breakdown |
| No model-switch planning | **Model Advisor** scenarios |
| No public LLM price overlay | **Price Watch** |

## What is read (after grant)

- `CORTEX_AI_FUNCTIONS_USAGE_HISTORY` (preferred) or `CORTEX_AISQL_USAGE_HISTORY`
- AI/Cortex-related rows from `METERING_HISTORY` (≤ 90 days)

Never: `QUERY_HISTORY`, SQL text, network egress, writes outside the app schema.

Optional: bind **AI Model & Compute Price Intelligence** views for weekly live prices; otherwise a bundled snapshot is used.

## Trust

Un-obfuscated source: https://github.com/dgvj-work/ai-price-intelligence  
Support: digvijay.vaghela@yahoo.com  
Changelog: `CHANGELOG.md`
