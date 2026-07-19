# Marketplace listing copy

Primary support: https://github.com/dgvj-work/ai-price-intelligence/discussions  
Contact: digvijay.vaghela@yahoo.com | Source: https://github.com/dgvj-work/ai-price-intelligence

---

## Listing A - Dataset

### Title
AI Model & Compute Price Intelligence

### Subtitle
Weekly LLM, GPU, and Snowflake Cortex prices with full history - public sources, full provenance.

### Category / tags (suggestions)
- Category: AI & ML / Data Enrichment
- Tags: `llm`, `pricing`, `gpu`, `cortex`, `benchmarks`, `finops`, `marketplace-data`

### Listing images (attach in Provider Studio)
- `docs/screenshots/dataset-model-current.png`
- `docs/screenshots/cost-per-mmlu.png`

### Description (benefit-led)

Stop screenshotting vendor pricing pages.

**AI Model & Compute Price Intelligence** is a weekly-refreshed Snowflake dataset of public LLM/embedding list prices, quality benchmarks, cloud GPU instance prices, and Snowflake Cortex credit rates - with SCD Type 2 history so you can see what changed and when.

**History note:** Price history accumulates from your first successful weekly refresh after publish (it is not a multi-year backfill). `VW_PRICE_CHANGES_90D` fills in as prices change over subsequent weeks.

Every fact row includes `source_url` and `retrieved_at`. We build only from public, redistributable sources (provider pricing pages, official cloud pricing APIs, public leaderboards). Seeds for LLM list prices are human-curated weekly; AWS/Azure/GCP GPU prices are pulled from public APIs.

Use it to:

- Compare GPT-4-class model prices over time
- Find the cheapest model above a quality bar (e.g. MMLU >= 85)
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

## Listing B - Native App

### Title
Cortex Cost Advisor

### Subtitle
Ranked Cortex model-switch savings, spend spikes, and price context. FinOps decisions, not another credit chart.

### Category / tags (suggestions)
- Category: AI & ML / Cost Management
- Tags: `cortex`, `finops`, `native-app`, `recommendations`, `read-only`

### Listing images (attach in Provider Studio)

Capture from the **installed v1.2.7+** app (preview sample data is fine). First open is **Getting started**; also show Advisor with recommendations (not an empty Overview):

1. `docs/screenshots/app-getting-started.png` (optional but recommended) — privilege callout / GRANT steps
2. `docs/screenshots/app-advisor.png` — **Advisor**: primary switch recommendation + metric strip + switch savings chart
3. `docs/screenshots/app-switches.png` — **Switches**: ranked scenario cards / matrix

How to capture: open Streamlit → **Getting started** (default) or **Advisor** / **Switches** → full browser window → PNG. Retire old `app-overview.png` / `app-model-advisor.png` names in Provider Studio.

### Description

**Cortex Cost Advisor** (v1.2.7) is for FinOps / platform teams deciding **which Cortex models to allow or migrate**.

**Every open starts on Getting started** so installers see the exact privilege story first (one ACCOUNTADMIN GRANT; Connect cannot self-grant). Preview mode uses **sample** usage so you can evaluate recommendations before granting. Then open **Advisor** for ranked recommendations such as: "Switch model A -> B: save ~X credits (~$Y est.)", plus concentration risk, spend-spike detection, and a simple forward estimate. Min switch savings % is configurable (default 15%; many teams use 25%+).

**Not a Snowsight clone.** Account credit rollups stay in Snowflake's native cost UI. This app adds same-token **Cortex switch scenarios** and Cortex-only anomaly/concentration signals. **Price Watch** is secondary (optional public list-price context when you bind the companion dataset; otherwise a bundled snapshot).

**Pages:** Getting started | Advisor | Switches | Price Watch (secondary) | Spend detail | Trust

USD figures use **your** entered $/credit (apps cannot read contracted rates). Analysis window up to **365 days**. No alerts/notifications yet; use Snowflake budgets / resource monitors for ongoing spend control.

### Privacy / trust (prominently display)

> Read-only. Requests **Imported Privileges on SNOWFLAKE** to read Cortex AI usage + AI/Cortex metering (Native Apps cannot take a single-view grant).  
> Does **not** read QUERY_HISTORY / SQL text.  
> No network, external access, or SPCS. No external telemetry; optional in-app diagnostic codes stay in your account.  
> Un-obfuscated source. Preview recommendations before granting.  
> ACCOUNT_USAGE can lag ~45 minutes.

Optional: bind Marketplace price dataset views for weekly rates; otherwise bundled snapshot. The companion dataset is **not required** for Advisor / Switches.

**Support:** [GitHub Discussions](https://github.com/dgvj-work/ai-price-intelligence/discussions) (preferred)  
**Contact:** digvijay.vaghela@yahoo.com  
**Source:** https://github.com/dgvj-work/ai-price-intelligence
