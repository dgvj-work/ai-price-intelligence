# Cortex Cost Advisor (v1.1.0)

**Advisor for Cortex model spend** — ranked switch savings, concentration/spike signals, and price context. Not a generic credit report.

## Who it’s for

FinOps / platform engineers deciding **which Cortex models to allow or migrate**.

## What you see first

On **Advisor**: a primary recommendation such as  
“Switch model A → B: save ~X credits (~$Y est.) in this window” — plus concentration, anomalies, and a simple forward estimate.

Preview mode uses sample usage so you can evaluate recommendations before granting privileges.

## Connect live usage

```sql
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO APPLICATION CORTEX_COST_ADVISOR;
```

Then open the app (views bind on session start) or click **Connect live usage**.

## Why not only Snowsight / raw SQL?

| Alone | This app |
|-------|----------|
| Credit rollups | Ranked **same-token switch** recommendations |
| Manual spreadsheets | Concentration + spike detection on Cortex |
| No public LLM overlay | Price Watch against models you used |

## Security

Reads Cortex / AI ACCOUNT_USAGE only (up to 365 days). Never QUERY_HISTORY. Zero egress. Un-obfuscated source.

USD figures use **your** entered $/credit — Snowflake does not expose contracted rates to apps.

## Support

digvijay.vaghela@yahoo.com · https://github.com/dgvj-work/ai-price-intelligence · `CHANGELOG.md`
