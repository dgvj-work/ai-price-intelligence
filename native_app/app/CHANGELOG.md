# Cortex Cost Advisor changelog

## 1.1.8 - 2026-07-19

Visual polish (native Streamlit only, no HTML/CSS inject):

- Bordered recommendation panels, clearer section hierarchy, quieter dataframes.
- Sidebar data status + calmer planning-input layout.
- Advisor: "At a glance" metrics + paired secondary findings.
- Getting started / Trust: stay-updated links; Provider Studio analytics documented in runbook.

## 1.1.6 - 2026-07-19

Copy polish:

- Remove em dashes, curly quotes, ellipsis characters, and similar typography from consumer-facing UI and package docs.

## 1.1.5 - 2026-07-19

Getting started depth:

- Full privilege map: required `IMPORTED PRIVILEGES`, warehouse, app role `APP_USER`.
- Exact `ACCOUNT_USAGE` objects unlocked; clarify **no** consumer DB/schema/table grants.
- Optional Price Intelligence reference binds (`SELECT` on three `SHARE.VW_*` views).
- Auto-granted in-app objects table + security-review checklist + troubleshooting.

## 1.1.4 - 2026-07-19

Consumer onboarding:

- New sidebar tab **Getting started** - install-to-value walkthrough, GRANT SQL, page map, FAQ.
- Preview mode opens on Getting started; live usage opens on Advisor.
- Connect-live CTA lives on the starter guide (and still on Advisor).

## 1.1.3 - 2026-07-19

Marketplace scan hardening:

- Remove all `unsafe_allow_html=True` / injected CSS from Streamlit UI.
- Hero + recommendation cards use native `st.title` / `st.success` / `st.info` only.

## 1.1.2 - 2026-07-19

Deployment hygiene + Marketplace review polish:

- Sync version label everywhere to **1.1.2** (`manifest.yml`, `APP_VERSION`, package).
- Credit price persist via **parameterized** Snowpark SQL binds (no float f-string).
- Distinguish **live load failure** vs empty usage (warning + sample, not silent demo).
- Canonical model-id matching (`model_ids.py`) - no loose `"llama"` substring hits.
- Price Watch: top 5 insights + expander for full overlapping list.
- Support via GitHub Discussions (sidebar + Trust).
- Require `ALTER APPLICATION ... UPGRADE` / `snow app run` so consumers see Advisor nav.

## 1.1.1 - 2026-07-19

P0 hardening:

- Theme: remove Google Fonts `@import`; system font stacks only (no egress).
- Session: sanitize procedure tokens so `EMPTY_STUB` never reaches the UI.
- Persist credit $/rate in `APP_SCHEMA.USER_SETTINGS` across sessions.
- SQL day windows clamped to int `[1, 365]` before f-string interpolation.
- Price Watch flags only models from the usage window (no hardcoded vendor list).

## 1.1.0 - 2026-07-19

Product rethink - **advisor, not report**:

- New **Advisor** home: ranked model-switch savings, concentration risk, spend spikes, forward estimate, price-move context.
- Recommendation engine (`insights.py`) - logic beyond raw ACCOUNT_USAGE SELECT.
- Navigation: Advisor -> Switches -> Price Watch -> Spend detail -> Trust.
- Analysis window up to **365 days** (views + UI).
- Credit rate input reframed as **your contract $/credit** (estimates only; apps cannot read negotiated rates).
- Silent session bind of passthrough views; removed "refresh" as a primary product control.
- Custom FinOps styling; Trust page answers buyer / moat / privilege questions.

## 1.0.1 - 2026-07-19

Preview-on-install sample data, guided connect, hide internal stubs, 1.0.x labeling.

## 1.0.0 - 2026-07-18

Initial Marketplace-oriented package.
