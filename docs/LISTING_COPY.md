# Marketplace listing copy

Support: digvijay.vaghela@yahoo.com · Source: https://github.com/dgvj-work/ai-price-intelligence

---

## Listing A — Dataset

### Title
AI Model & Compute Price Intelligence

### Subtitle
Weekly LLM, GPU, and Snowflake Cortex prices with full history — public sources, full provenance.

### Category / tags (suggestions)
- Category: AI & ML / Data Enrichment
- Tags: `llm`, `pricing`, `gpu`, `cortex`, `benchmarks`, `finops`, `marketplace-data`

### Listing images (attach in Provider Studio)
- `docs/screenshots/dataset-model-current.png`
- `docs/screenshots/cost-per-mmlu.png`

### Description (benefit-led)

Stop screenshotting vendor pricing pages.

**AI Model & Compute Price Intelligence** is a weekly-refreshed Snowflake dataset of public LLM/embedding list prices, quality benchmarks, cloud GPU instance prices, and Snowflake Cortex credit rates — with SCD Type 2 history so you can see what changed and when.

**History note:** Price history accumulates from your first successful weekly refresh after publish (it is not a multi-year backfill). `VW_PRICE_CHANGES_90D` fills in as prices change over subsequent weeks.

Every fact row includes `source_url` and `retrieved_at`. We build only from public, redistributable sources (provider pricing pages, official cloud pricing APIs, public leaderboards). Seeds for LLM list prices are human-curated weekly; AWS/Azure/GCP GPU prices are pulled from public APIs.

Use it to:

- Compare GPT-4-class model prices over time
- Find the cheapest model above a quality bar (e.g. MMLU ≥ 85)
- Benchmark H100 on-demand $/GPU-hour across clouds and regions
- Convert Cortex credits into planning scenarios alongside external API prices

**Refresh cadence:** Weekly (Mondays). Check `VW_META_REFRESH_LOG` for the latest successful load.

**Support:** digvijay.vaghela@yahoo.com  
**Source:** https://github.com/dgvj-work/ai-price-intelligence

### Sample SQL (5)

```sql
-- 1) Compare GPT-4-class model prices over time
SELECT MODEL_ID, VALID_FROM, VALID_TO, IS_CURRENT,
       PRICE_INPUT_USD_PER_1M_TOKENS, PRICE_OUTPUT_USD_PER_1M_TOKENS, SOURCE_URL
FROM <DB>.SHARE.FACT_MODEL_PRICE_HISTORY
WHERE MODEL_ID ILIKE '%gpt-4%' OR MODEL_ID ILIKE '%sonnet%' OR MODEL_ID ILIKE '%gemini%'
ORDER BY MODEL_ID, VALID_FROM;

-- 2) Cheapest model above 85 MMLU (current prices)
SELECT *
FROM <DB>.SHARE.VW_COST_PER_BENCHMARK_POINT
WHERE SCORE >= 85
ORDER BY PRICE_INPUT_USD_PER_1M_TOKENS ASC
LIMIT 20;

-- 3) H100 on-demand price by cloud & region
SELECT CLOUD, INSTANCE_NAME, GPU_MODEL, REGION,
       PRICE_ON_DEMAND_USD_HR, SOURCE_URL, RETRIEVED_AT
FROM <DB>.SHARE.VW_GPU_CURRENT
WHERE UPPER(GPU_MODEL) LIKE '%H100%'
ORDER BY PRICE_ON_DEMAND_USD_HR NULLS LAST;

-- 4) Cortex credit rates currently in force
SELECT FUNCTION_NAME, MODEL_NAME, CREDITS_PER_1M_TOKENS, SOURCE_URL, RETRIEVED_AT
FROM <DB>.SHARE.VW_CORTEX_CURRENT
ORDER BY CREDITS_PER_1M_TOKENS DESC;

-- 5) Every model price change in the last 90 days
SELECT *
FROM <DB>.SHARE.VW_PRICE_CHANGES_90D
ORDER BY CHANGED_AT DESC;
```

### Usage examples

- FinOps dashboards for AI spend planning
- Join to your own Cortex usage (or install **Cortex Cost Advisor**) for switch scenarios
- Competitive monitoring via `VW_PRICE_CHANGES_90D`

---

## Listing B — Native App

### Title
Cortex Cost Advisor

### Subtitle
Free, read-only Streamlit app: your Cortex spend, model-switch savings, and price-change alerts.

### Category / tags (suggestions)
- Category: AI & ML / Cost Management
- Tags: `cortex`, `finops`, `native-app`, `streamlit`, `read-only`

### Listing images (attach in Provider Studio)
- `docs/screenshots/app-overview.png`
- `docs/screenshots/app-model-advisor.png`

### Description

**Cortex Cost Advisor** (v1.0.1) turns Snowflake account-usage metadata into a clear AI spend picture — without sending anything outside your account. On first open it shows **labeled preview charts** (sample Cortex spend) so consumers see value immediately; admins then use **Connect live usage** (grant SQL + one click) to switch to ACCOUNT_USAGE.

**Pages**

1. **Overview** — Cortex credits + USD estimate (you set credit price; default $3.00), trend, top functions/models, 30/60/90-day windows. Notes ACCOUNT_USAGE lag (~45 minutes).
2. **Model Advisor** — for models you actually use, estimate credits if the same tokens ran on alternative Cortex models. Uses bound Marketplace dataset references when available; otherwise a bundled snapshot.
3. **Price Watch** — recent price changes, flagged when they overlap your active models.
4. **About / Trust** — security & permissions: why `IMPORTED PRIVILEGES ON SNOWFLAKE DB` is required, what is read, and what never happens.

### Privacy / trust (prominently display)

> This app is **read-only** and **self-contained**. It requests **Imported Privileges on the SNOWFLAKE database** so it can read Cortex AI function usage + metering views inside your account. Snowflake Native Apps do not support granting a single ACCOUNT_USAGE view; this privilege is the documented mechanism.  
> It does **not** read QUERY_HISTORY / SQL text.  
> It does **not** use external access integrations, external functions, network calls, Snowpark Container Services, or telemetry.  
> It does **not** write outside the application’s own schema.  
> Nothing leaves your Snowflake account. Application code is un-obfuscated and inspectable.  
> Queries are capped at 90 days. ACCOUNT_USAGE can lag live activity by up to ~45 minutes.

Optional: bind Marketplace dataset references (`VW_MODEL_CURRENT`, `VW_CORTEX_CURRENT`, `VW_PRICE_CHANGES_90D`) for live weekly prices. Without bindings, the app still works using a bundled snapshot.

**Support:** digvijay.vaghela@yahoo.com  
**Source:** https://github.com/dgvj-work/ai-price-intelligence
