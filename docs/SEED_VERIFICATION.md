# Seed verification log

Contact: digvijay.vaghela@yahoo.com  
Last bulk verification pass: **2026-07-18**

| Source | Checked | Notes |
|---|---|---|
| OpenAI Platform Pricing | Yes | https://platform.openai.com/docs/pricing — gpt-4o, gpt-4o-mini, gpt-4.1, gpt-4.1-mini, o3-mini, text-embedding-3-large confirmed |
| Anthropic API Pricing | Yes | https://www.anthropic.com/pricing — Sonnet 4.6 $3/$15, Opus 4.8 $5/$25, Haiku 4.5 $1/$5 |
| Snowflake SCT | Yes | https://www.snowflake.com/legal-files/CreditConsumptionTable.pdf (effective 2026-07-17) — Cortex rates updated to Table 6 **input** credits/MTok (output noted in YAML comments where different) |
| Google / DeepSeek / Mistral / Cohere / Amazon / xAI | Best-effort | Public pages change often; re-check before major listing updates |
| Meta / Llama hosted | Representative | Hosted API prices (Together-class), **not** Meta list — flagged in `tier_notes` |
| GPU seeds | Approximate | Fallback until live AWS/Azure APIs override in refresh |

## Field convention (Cortex)

`credits_per_1m_tokens` stores the Snowflake **input** token credit rate from the Service Consumption Table. Where input ≠ output, see YAML comments for the output rate. Model Advisor scenarios are therefore input-oriented estimates.
