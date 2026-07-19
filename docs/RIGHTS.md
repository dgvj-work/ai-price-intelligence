# Data rights & redistribution

**Provider contact:** digvijay.vaghela@yahoo.com  
**Source repo:** https://github.com/dgvj-work/ai-price-intelligence

## What we publish

This Marketplace dataset redistributes **public list prices and public benchmark scores** collected from:

- Vendor API pricing pages (e.g. OpenAI Platform Pricing, Anthropic Claude API pricing)
- Public cloud retail / price-list APIs (AWS Price List, Azure Retail Prices, GCP Billing catalog where available)
- Snowflake Service Consumption Table (public PDF) for Cortex credit rates
- Public model cards / blog posts / leaderboards for benchmark scores

Every fact row includes `source_url` and `retrieved_at` so consumers can audit provenance.

## What we do **not** publish

- Negotiated / private / enterprise-only pricing
- Non-public rate cards
- Scraped HTML that violates a site’s terms (seeds are curated from public pages; cloud GPUs from public APIs)

## Consumer use

Consumers may query the shared secure views for internal FinOps, analytics, and planning. This is a **free** listing. Redistribution of the share itself outside Snowflake Marketplace terms is governed by Snowflake’s listing agreement.

## Accuracy

List prices change. We refresh weekly. Treat values as planning estimates and confirm material decisions against the linked `source_url`.
