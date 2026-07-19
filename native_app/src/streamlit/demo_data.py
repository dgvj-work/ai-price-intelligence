"""Deterministic preview data so Advisor shows recommendations before privileges."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

# Synthetic usage skewed so switch recommendations and spikes are visible in preview.
_DEMO_MODELS = [
    ("COMPLETE", "claude-4-sonnet", 8_200_000, 14.76),
    ("COMPLETE", "mistral-large2", 12_500_000, 15.00),
    ("COMPLETE", "llama3.1-70b", 42_000_000, 18.14),
    ("EMBED_TEXT_768", "snowflake-arctic-embed-m", 95_000_000, 2.85),
]


def demo_usage_by_model() -> pd.DataFrame:
    rows = [
        {
            "MODEL_NAME": model,
            "FUNCTION_NAME": fn,
            "TOKENS": tokens,
            "CREDITS": credits,
        }
        for fn, model, tokens, credits in _DEMO_MODELS
    ]
    return pd.DataFrame(rows)


def demo_cortex_top() -> pd.DataFrame:
    return demo_usage_by_model()[
        ["FUNCTION_NAME", "MODEL_NAME", "CREDITS", "TOKENS"]
    ].sort_values("CREDITS", ascending=False)


def demo_cortex_spend(days: int = 30) -> pd.DataFrame:
    """Spread demo credits across days; inject one spike for anomaly demos."""
    days = max(14, min(int(days), 365))
    end = date.today()
    start = end - timedelta(days=days - 1)
    usage = demo_usage_by_model()
    total_credits = float(usage["CREDITS"].sum())
    total_tokens = float(usage["TOKENS"].sum())

    weights: list[float] = []
    day_list: list[date] = []
    cur = start
    while cur <= end:
        day_list.append(cur)
        w = 1.35 if cur.weekday() < 5 else 0.55
        weights.append(w)
        cur += timedelta(days=1)

    # Spike ~5 days ago for anomaly insight.
    spike_day = end - timedelta(days=5)
    for i, d in enumerate(day_list):
        if d == spike_day:
            weights[i] *= 3.2

    wsum = sum(weights) or 1.0
    rows: list[dict[str, object]] = []
    for _, u in usage.iterrows():
        share_c = float(u["CREDITS"]) / total_credits if total_credits else 0.0
        share_t = float(u["TOKENS"]) / total_tokens if total_tokens else 0.0
        for d, w in zip(day_list, weights):
            frac = w / wsum
            rows.append(
                {
                    "DAY": pd.Timestamp(d),
                    "FUNCTION_NAME": u["FUNCTION_NAME"],
                    "MODEL_NAME": u["MODEL_NAME"],
                    "TOKENS": round(total_tokens * share_t * frac, 0),
                    "CREDITS": round(total_credits * share_c * frac, 4),
                }
            )
    return pd.DataFrame(rows)
