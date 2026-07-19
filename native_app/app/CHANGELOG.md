# Cortex Cost Advisor changelog

## 1.1.1 — 2026-07-19

P0 hardening (Coco review items, applied in-repo):

- Theme: remove Google Fonts `@import`; system font stacks only (no egress).
- Session: sanitize procedure tokens so `EMPTY_STUB` never reaches the UI.
- Persist credit $/rate in `APP_SCHEMA.USER_SETTINGS` across sessions.
- SQL day windows clamped to int `[1, 365]` before f-string interpolation.
- Price Watch flags only models from the usage window (no hardcoded vendor list).

## 1.1.0 — 2026-07-19

Product rethink — **advisor, not report**:

- New **Advisor** home: ranked model-switch savings, concentration risk, spend spikes, forward estimate, price-move context.
- Recommendation engine (`insights.py`) — logic beyond raw ACCOUNT_USAGE SELECT.
- Navigation: Advisor → Switches → Price Watch → Spend detail → Trust.
- Analysis window up to **365 days** (views + UI).
- Credit rate input reframed as **your contract $/credit** (estimates only; apps cannot read negotiated rates).
- Silent session bind of passthrough views; removed “refresh” as a primary product control.
- Custom FinOps styling; Trust page answers buyer / moat / privilege questions.

## 1.0.1 — 2026-07-19

Preview-on-install sample data, guided connect, hide internal stubs, 1.0.x labeling.

## 1.0.0 — 2026-07-18

Initial Marketplace-oriented package.
