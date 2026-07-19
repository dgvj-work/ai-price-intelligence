# Design Decisions & Assumptions

This document records defaults chosen so the product can ship without blocking clarifications.
Anything deferred lives here — not as `TODO` comments in code.

## Product scope

| Decision | Choice |
|---|---|
| Dataset product name | **AI Model & Compute Price Intelligence** |
| Native app name | **Cortex Cost Advisor** |
| Pricing model | Both listings are **free** (Marketplace freemium trust play) |
| Refresh cadence | Weekly (Mondays 06:00 UTC via GitHub Actions) |
| Snowflake credit USD default (app) | **$3.00** (user-overridable in UI) |
| History window in app queries | Cap at **90 days** (no unbounded scans) |
| App privileges | `IMPORTED PRIVILEGES ON SNOWFLAKE DB` only — no `EXECUTE TASK`, no external access |

## Architecture

1. **Seeds-first for LLM pricing & benchmarks.** Public pricing pages change HTML/layout constantly; YAML seeds under `ingestion/sources/seeds/` are the curated source of truth. Cloud GPU pricing is API-automated (AWS / Azure / GCP public endpoints).
2. **SCD2 only on value change.** Closing a current row and opening a new one happens only when a tracked price field differs (normalized). History rows are never mutated.
3. **Provenance on every fact.** `source_url` + `retrieved_at` are required on all price and benchmark facts.
4. **Share surface = secure views only.** Consumers never see base tables; freshness is exposed via `VW_META_REFRESH_LOG`.
5. **Native app is standalone-capable.** If the Marketplace dataset share is not mounted, Model Advisor / Price Watch fall back to a bundled static snapshot CSV vendored in the app package.

## Identifiers & naming

| Entity | ID scheme |
|---|---|
| Providers | `slug` e.g. `openai`, `anthropic`, `aws` |
| Models | `{provider}:{model_slug}` e.g. `openai:gpt-4o` |
| GPU instances | `{cloud}:{instance_name}` e.g. `aws:p5.48xlarge` |
| Cortex rows | `{function}:{model}` e.g. `COMPLETE:llama3.1-70b` |

Database / schemas: `AI_PRICE_INTEL.{RAW,CURATED,SHARE}`.

## Ingestion

| Topic | Decision |
|---|---|
| Dry-run | `--dry-run` writes Parquet under `/tmp/ai_price_intel/<run_id>/` — no Snowflake connection |
| Currency | All amounts normalized to **USD** |
| Token units | Always **per 1M tokens** |
| GPU units | Always **USD per GPU-hour** for reserved/spot/on-demand (instance-hour ÷ gpu_count when APIs quote instance-hour) |
| GPU filter | Instance families containing H100, A100, L4, L40S, V100, T4, A10, A10G |
| AWS API | Public Price List bulk API (no auth); On-Demand primary (spot deferred — see below) |
| GPU seed fallback | `gpu_instances.yaml` always loads; cloud APIs override matching keys when available |
| Azure API | Retail Prices API (no auth), filter `productName` / `armSkuName` for GPU VMs |
| GCP API | Public Cloud Billing SKU catalog (`cloudbilling.googleapis.com` list public SKUs path used by community scrapers) — see note below |
| HF leaderboards | Optional enrichment; seeds remain authoritative if HF is unreachable |
| Auth for Snowflake load | Key-pair via env (`SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PRIVATE_KEY_PATH`, optional `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE`) |
| Quality gate | `run_refresh.py` exits non-zero if SQL quality checks fail |

**GCP note:** Official GCP pricing often requires a GCP project + API enablement. We use the publicly documented Cloud Billing Catalog HTTP endpoint with polite retries; if it fails in CI, GPU rows for GCP are skipped with a warning (AWS/Azure still load). Documented in the runbook.

## Native app security posture

- Read-only: only `ACCOUNT_USAGE` / metering views via imported privileges.
- No external access integrations, external functions, network calls, SPCS, or telemetry.
- No writes outside the application’s own schema.
- All Python un-obfuscated; Streamlit + vendored snapshot only.
- Cortex usage: prefer `CORTEX_AI_FUNCTIONS_USAGE_HISTORY`, fall back to `CORTEX_AISQL_USAGE_HISTORY`. Never use deprecated `CORTEX_FUNCTIONS_USAGE_HISTORY`.
- No `QUERY_HISTORY` access (avoids reading SQL text).
- ACCOUNT_USAGE views are (re)created by `ENSURE_ACCOUNT_USAGE_VIEWS()` so they work after the consumer grants imported privileges post-install; Streamlit calls this on session start.
- Optional Marketplace dataset access uses Native App **references** (`price_intel_*`), not INFORMATION_SCHEMA discovery.

## Dataset seed values

OpenAI, Anthropic, and Cortex (SCT) seeds were verified **2026-07-18** (see `docs/SEED_VERIFICATION.md`). Other providers remain best-effort and should be re-checked on the weekly ops cadence.

## Deferred (intentionally out of v1)

| Item | Rationale |
|---|---|
| Provider-authenticated private pricing tiers | Not redistributable / not public |
| Spot / reserved GPU automation | On-demand only in v1; spot/reserved columns exist but stay NULL until a verified source is wired |
| Backfilled multi-year price history | History starts at first successful publish and grows weekly; listing copy states this clearly |
| Multi-currency display | Normalize to USD only in v1 |
| App write-back / recommendations persisted | Violates read-only / minimal privilege posture |
| Snowpark Container Services | Excluded by hard constraint |
| Automated HTML scraping of LLM vendor pages | Brittle; seeds-first instead |
| Paid listing / monetization hooks | Free listing first; revisit after traction |

## Support & legal placeholders

- Support contact: `digvijay.vaghela@yahoo.com`
- Public repo: https://github.com/dgvj-work/ai-price-intelligence
- License: Apache-2.0 for this repository.
- Marketplace provider profile: create in Snowflake Provider Studio before first listing (see `docs/PUBLISHING_RUNBOOK.md`).
- Rights memo: `docs/RIGHTS.md`
