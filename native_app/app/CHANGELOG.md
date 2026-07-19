# Cortex Cost Advisor changelog

## 1.2.7 - 2026-07-19

Release cut for Marketplace submit: always open on **Getting started**, keep
`__pycache__` off the stage, and align listing copy with the installed UX.

## 1.2.6 - 2026-07-19

P0: fix `V_CORTEX_USAGE` for `CORTEX_AI_FUNCTIONS_USAGE_HISTORY`. Replace the
correlated `FLATTEN` scalar subquery (and the nested `LATERAL (SELECT…)` form,
both fail with "Unsupported subquery type") with `LEFT JOIN LATERAL FLATTEN`
plus `GROUP BY`. Probe `SELECT COUNT(*)` after CREATE VIEW so Connect cannot
report live when the view is not queryable.

## 1.2.5 - 2026-07-19

Preview / Connect UX: make sample-data mode explicit, show GRANT SQL in the
sidebar, and surface clear feedback when Connect finds privileges still missing
(apps cannot self-grant IMPORTED PRIVILEGES).

## 1.2.4 - 2026-07-19

Fix Streamlit load failure: Snowflake warehouse Anaconda rejects pip-style
`>=` / `<` pins. Use `=` and `*` ranges in `environment.yml`.

## 1.2.3 - 2026-07-19

Marketplace review hardening:

- Configurable **minimum switch savings %** (sidebar; persisted). Documented insight thresholds.
- Pin Streamlit/pandas/Snowpark/Altair versions in `environment.yml`.
- App-schema diagnostics for load failures (copyable code; no egress).
- Remove unused embedded logo blob; text brand mark only.
- Consolidate historical changelog dates (fewer same-day entries).

## 1.2.0 - 2026-07-12

Visual identity + charts (native Streamlit / Altair; no HTML injection):

- FinOps teal theme via `.streamlit/config.toml`.
- Branded spend / switch / Price Watch charts; metric sparklines.
- Primary vs secondary recommendation panels; Getting started walkthrough.
- Support via GitHub Discussions (+ publisher email).

## 1.1.0 - 2026-07-01

Advisor product + Marketplace scan hygiene:

- Insight-first Advisor (switches, concentration, spikes, forward estimate, price moves).
- Navigation: Getting started, Advisor, Switches, Price Watch, Spend detail, Trust.
- Remove `unsafe_allow_html` / external fonts; parameterized settings SQL.
- Canonical model-id matching; load-error vs empty-usage UX; credit rate persistence.

## 1.0.0 - 2026-06-18

Initial Marketplace-oriented Native App package (preview sample data, guided connect, ACCOUNT_USAGE views).
