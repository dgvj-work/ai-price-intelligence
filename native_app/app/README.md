# Cortex Cost Advisor

A **free, read-only** Snowflake Native App that helps you understand Cortex / AI SQL spend and compare model pricing scenarios.

## What this app reads

With your approval of **Imported Privileges on the SNOWFLAKE database**, the app reads:

- `SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY` (preferred; data from 2026-01-05+)
- or `SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AISQL_USAGE_HISTORY` (fallback)
- AI/Cortex-related rows from `SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY` (last 90 days)

It does **not** read `QUERY_HISTORY` or any query text.

After you grant imported privileges, open the app once — it calls `ENSURE_ACCOUNT_USAGE_VIEWS()` so usage views are created against the live ACCOUNT_USAGE objects.

### Optional Marketplace dataset

Bind these references (Snowsight → app privileges / references) to the **AI Model & Compute Price Intelligence** listing for live prices:

- `price_intel_model_current` → `…SHARE.VW_MODEL_CURRENT`
- `price_intel_cortex_current` → `…SHARE.VW_CORTEX_CURRENT`
- `price_intel_price_changes` → `…SHARE.VW_PRICE_CHANGES_90D`

If unbound, Model Advisor / Price Watch use a bundled CSV snapshot so the app still works standalone.

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
