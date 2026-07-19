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

## 5) Native app — local + security scan

```bash
cd native_app
snow app run
# or: snow app deploy
```

Set package distribution external to trigger automated security scan:

```sql
ALTER APPLICATION PACKAGE cortex_cost_advisor_pkg
  SET DISTRIBUTION = EXTERNAL;
```

Then:

1. Push a version/patch per Snowflake Native Apps workflow (`snow app version create` / Provider Studio).
2. **Private share** the app to a second test account.
3. Install on the test account, grant **Imported Privileges on SNOWFLAKE DB**, open Streamlit, click **Refresh usage views**, verify Overview (empty-state OK if no Cortex yet).
4. Optionally mount the data listing and bind references:
   - `price_intel_model_current` → `…SHARE.VW_MODEL_CURRENT`
   - `price_intel_cortex_current` → `…SHARE.VW_CORTEX_CURRENT`
   - `price_intel_price_changes` → `…SHARE.VW_PRICE_CHANGES_90D`
5. Set a Streamlit query warehouse in Snowsight if the app prompts for one.
6. Submit the **app listing** (Listing B copy). Emphasize the privacy paragraph.

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

1. Monday morning (or before cron): update YAML seeds (~15 min), especially rows marked `VERIFY BEFORE FIRST PUBLISH`.
2. CI dry-run on PR; scheduled workflow loads Snowflake.
3. If Action fails, read job log (no webhooks) and fix seeds/API issues.

## 8) Rollback

- Data: SCD2 never mutates history; republish corrected current rows via a new refresh.
- App: deploy previous application package version; keep `DISTRIBUTION=EXTERNAL` only when ready for scan.
