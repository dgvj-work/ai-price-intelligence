# Cortex Cost Advisor (v1.2.7)

**Advisor for Cortex model spend**: ranked switch savings, concentration/spike signals, and price context. Not a generic credit report.

## Who it's for

FinOps / platform engineers deciding **which Cortex models to allow or migrate**.

## In-app starter guide

After install, open the sidebar tab **Getting started**. It covers:

- Privilege map (required vs optional vs automatic vs never requested)
- Exact `ACCOUNT_USAGE` objects unlocked by `IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE`
- Confirmation that **no** grants on your databases / schemas / tables are needed
- Warehouse + application role `APP_USER`
- Optional binds to Price Intelligence `SHARE.VW_*` views (`SELECT` only)
- Troubleshooting checklist for security review

Every open lands on **Getting started** first (preview or live).

## What you see on Advisor

A primary recommendation such as  
"Switch model A -> B: save ~X credits (~$Y est.) in this window", plus concentration, anomalies, and a simple forward estimate.

Preview mode uses sample usage so you can evaluate recommendations before granting privileges.

## Connect live usage

```sql
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO APPLICATION CORTEX_COST_ADVISOR;
```

Then open **Getting started** (or Advisor) and click **Connect live usage**. Views also bind on session start once the GRANT exists.

## Why not only Snowsight / raw SQL?

| Alone | This app |
|-------|----------|
| Credit rollups | Ranked **same-token switch** recommendations |
| Manual spreadsheets | Concentration + spike detection on Cortex |
| No public LLM overlay | Price Watch against models you used |

## Security

Reads Cortex / AI ACCOUNT_USAGE only (up to 365 days). Never QUERY_HISTORY. Zero egress. Un-obfuscated source.

USD figures use **your** entered $/credit. Snowflake does not expose contracted rates to apps.

## Support

Support: https://github.com/dgvj-work/ai-price-intelligence/discussions | `CHANGELOG.md`
