# Publishing runbook

Click-by-click path from empty Snowflake account → Marketplace listings.

## 0) Prerequisites

- Snowflake account with ability to create shares / application packages (trial OK).
- `snow` CLI installed (`pip install snowflake-cli-labs` or current Snowflake CLI).
- Python 3.11, `make setup` completed locally.
- GitHub repo with Actions enabled.

## 1) Key-pair auth (no passwords)

On your laptop:

```bash
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8 -nocrypt
openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub
```

In Snowflake (as `ACCOUNTADMIN`):

```sql
CREATE ROLE IF NOT EXISTS AI_PRICE_ADMIN;
GRANT CREATE DATABASE ON ACCOUNT TO ROLE AI_PRICE_ADMIN;
GRANT CREATE SHARE ON ACCOUNT TO ROLE AI_PRICE_ADMIN;
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE AI_PRICE_ADMIN;

CREATE USER IF NOT EXISTS AI_PRICE_SVC
  TYPE = SERVICE
  RSA_PUBLIC_KEY = '<paste contents of rsa_key.pub without headers>'
  DEFAULT_ROLE = AI_PRICE_ADMIN
  DEFAULT_WAREHOUSE = COMPUTE_WH;

GRANT ROLE AI_PRICE_ADMIN TO USER AI_PRICE_SVC;
-- Prefer AI_PRICE_ADMIN over ACCOUNTADMIN for CI. Use ACCOUNTADMIN only for one-time bootstrap.
```

Export locally (see `.env.example`):

```bash
export SNOWFLAKE_ACCOUNT=...
export SNOWFLAKE_USER=AI_PRICE_SVC
export SNOWFLAKE_PRIVATE_KEY_PATH=/absolute/path/rsa_key.p8
export SNOWFLAKE_WAREHOUSE=COMPUTE_WH
export SNOWFLAKE_ROLE=AI_PRICE_ADMIN
```

### GitHub Actions secrets

| Secret | Value |
|---|---|
| `SNOWFLAKE_ACCOUNT` | account locator |
| `SNOWFLAKE_USER` | `AI_PRICE_SVC` |
| `SNOWFLAKE_ROLE` | `AI_PRICE_ADMIN` (preferred) |
| `SNOWFLAKE_WAREHOUSE` | warehouse name |
| `SNOWFLAKE_PRIVATE_KEY` | full PEM of `rsa_key.p8` |
| `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` | only if key is encrypted |

## 2) Deploy warehouse + first refresh

```bash
make deploy-warehouse
# First refresh can skip cloud APIs if you want seeds only:
python -m ingestion.run_refresh --skip-cloud
# Full refresh:
make refresh
```

Verify:

```sql
SELECT * FROM AI_PRICE_INTEL.SHARE.VW_META_REFRESH_LOG ORDER BY STARTED_AT DESC LIMIT 5;
SELECT COUNT(*) FROM AI_PRICE_INTEL.SHARE.VW_MODEL_CURRENT;
```

## 3) Provider profile (Provider Studio)

1. Snowsight → **Data Products** → **Provider Studio** (or Marketplace → Provider).
2. Create / complete **Provider Profile** (legal name, contact, logo, support email).
3. Wait for profile approval if required by Snowflake.

## 4) Publish data listing (SHARE-backed)

1. Confirm share exists: `SHOW SHARES LIKE 'AI_PRICE_INTEL_SHARE';`
2. Provider Studio → **Create Listing** → **Free** → **Share** → select `AI_PRICE_INTEL_SHARE`.
3. Paste copy from `docs/LISTING_COPY.md` (Listing A).
4. Regions: **All regions** (or your footprint).
5. Attach sample queries from listing copy.
6. Private share to a second test account first (`ALTER SHARE ... ADD ACCOUNTS = ...`) and validate selects.
7. Submit for Marketplace review / publish.

## 5) Native app: local + security scan

```bash
cd native_app
snow app run -c ai_price
# or: snow app deploy -c ai_price
```

### Named version + DEFAULT release directive (done for v1.1.6)

Marketplace consumers install from a **named** version (not stage/`UNVERSIONED` from `snow app run`):

```bash
cd native_app
snow app deploy -c ai_price
snow app version create V1_1_6 -c ai_price --label "1.1.6" --skip-git-check --force --no-interactive
```

```sql
ALTER APPLICATION PACKAGE CORTEX_COST_ADVISOR_PKG
  MODIFY RELEASE CHANNEL DEFAULT ADD VERSION V1_1_6;

ALTER APPLICATION PACKAGE CORTEX_COST_ADVISOR_PKG
  MODIFY RELEASE CHANNEL DEFAULT
  SET DEFAULT RELEASE DIRECTIVE VERSION = V1_1_6 PATCH = 0;

-- Optional cleanup of unused versions (release-channels packages):
ALTER APPLICATION PACKAGE CORTEX_COST_ADVISOR_PKG DEREGISTER VERSION V1_1_2;
```

Current package state: **DEFAULT** and **ALPHA** directives point at **V1_1_6** patch 0.

### EXTERNAL distribution (security scan)

```sql
ALTER APPLICATION PACKAGE CORTEX_COST_ADVISOR_PKG
  SET DISTRIBUTION = EXTERNAL;
```

**Hard blocker on trial accounts:** Snowflake returns `093171` (cannot set EXTERNAL in trial orgs/accounts). Use a **non-trial provider account** (or convert the trial), then re-run the statement and wait for `review_status = APPROVED`.

Note: a local `snow app run` install stays stage-based and cannot `UPGRADE USING VERSION`. Validate Marketplace path by installing from the release directive on a second account.

Then:

1. On a non-trial account: set `DISTRIBUTION = EXTERNAL` and wait for security APPROVED.
2. **Private share** the app to a second test account.
3. Install from the release directive (not an `UNVERSIONED` debug install). Grant **Imported Privileges on SNOWFLAKE DB**, open Streamlit, use **Connect live usage** / reopen the app. Verify **Getting started** + **Advisor** preview -> connect -> live (empty Cortex spend is OK).
4. Optionally mount the data listing and bind references:
   - `price_intel_model_current` -> `<PRICE_DB>.SHARE.VW_MODEL_CURRENT`
   - `price_intel_cortex_current` -> `<PRICE_DB>.SHARE.VW_CORTEX_CURRENT`
   - `price_intel_price_changes` -> `<PRICE_DB>.SHARE.VW_PRICE_CHANGES_90D`
5. Set a Streamlit query warehouse in Snowsight if the app prompts for one.
6. Submit the **app listing** (Listing B copy). Emphasize the privacy paragraph.

## 5b) Provider adoption analytics (who installed)

You do **not** get company/user lists from inside the Native App UI. Zero egress is a Marketplace security win; saving an email to `USER_SETTINGS` only stores it in the **consumer** account (you cannot read it).

After the listing is published on a non-trial provider account, use Snowflake's provider views:

1. Snowsight: **Marketplace -> Provider Studio -> Analytics -> Detailed Metrics -> Listings Installed**
   - Shows consumer company (when available), account name, contact fields Snowflake has, region.
2. SQL (ACCOUNTADMIN on the **provider** account):

```sql
-- Install / uninstall / get events (latency up to ~2 days)
SELECT
  EVENT_DATE,
  EVENT_TYPE,
  LISTING_NAME,
  CONSUMER_ORGANIZATION,
  CONSUMER_ACCOUNT_NAME,
  CONSUMER_ACCOUNT_LOCATOR,
  CONSUMER_EMAIL,
  REGION_GROUP
FROM SNOWFLAKE.DATA_SHARING_USAGE.LISTING_EVENTS_DAILY
ORDER BY EVENT_DATE DESC;

-- App instance health across consumers
SELECT *
FROM SNOWFLAKE.DATA_SHARING_USAGE.APPLICATION_STATE
LIMIT 100;
```

Until the listing is live (and Provider Studio / `DATA_SHARING_USAGE` is available on that account), those views will be empty or inaccessible. Private shares and trial provider accounts often lack full Marketplace analytics.

Optional: in-app **Stay updated** links (GitHub Discussions / mailto) for voluntary intros. That is relationship outreach, not install telemetry.

## 6) Pre-submission security checklist

Mapped to Snowflake app security review expectations:

| Requirement | Status in this repo |
|---|---|
| No code obfuscation | ✅ Plain Python/SQL |
| Minimal privileges | ✅ Only `IMPORTED PRIVILEGES ON SNOWFLAKE DB` |
| Dependencies in package | ✅ `environment.yml` under Streamlit; no undeclared downloads |
| No secrets in code | ✅ Key-pair via env/CI secrets only |
| No external access / network | ✅ None requested |
| No external functions | ✅ None |
| No SPCS | ✅ None |
| No telemetry exfil | ✅ None |
| Read-only outside app schema | ✅ Views + Streamlit only |
| Consumer-facing privilege description | ✅ In `manifest.yml` |

## 7) Weekly ops

1. Monday morning (or before cron): update YAML seeds (~15 min); see `docs/SEED_VERIFICATION.md`.
2. CI dry-run on PR; scheduled workflow loads Snowflake.
3. If Action fails, read job log (no webhooks) and fix seeds/API issues.

## 8) Rollback

- Data: SCD2 never mutates history; republish corrected current rows via a new refresh.
- App: deploy previous application package version; keep `DISTRIBUTION=EXTERNAL` only when ready for scan.
