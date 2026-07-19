"""
Recommendation engine - the product moat beyond raw ACCOUNT_USAGE SELECT.

Produces actionable Advisor cards: model-switch savings, concentration risk,
spend anomalies, forward estimate, and price-move impact. This logic is not
what Snowsight cost UI ships today.

Threshold defaults (FinOps-tunable where noted):
- SWITCH_MIN_SAVINGS_PCT (default 0.15): only surface switches >= this % cheaper
  at list rates. Configurable in the app sidebar (many teams prefer 0.25+).
- CONCENTRATION_SHARE_PCT (0.55): flag when one model exceeds this share of credits.
- SPIKE_MEDIAN_MULT (2.5): flag days at/above this multiple of median daily credits.
- FORECAST_TRAIL_DAYS (14) x FORECAST_HORIZON_DAYS (30): trailing-average planning
  number (not ML).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

# Documented defaults — switch floor is also exposed in the Streamlit sidebar.
SWITCH_MIN_SAVINGS_PCT = 0.15
CONCENTRATION_SHARE_PCT = 0.55
SPIKE_MEDIAN_MULT = 2.5
FORECAST_TRAIL_DAYS = 14
FORECAST_HORIZON_DAYS = 30


@dataclass(frozen=True)
class Insight:
    kind: str  # switch | concentration | anomaly | forecast | price
    severity: str  # high | medium | info
    headline: str
    detail: str
    savings_credits: float = 0.0
    savings_usd: float = 0.0
    meta: dict[str, Any] | None = None


def _norm_prices(cortex_prices: pd.DataFrame) -> pd.DataFrame:
    if cortex_prices is None or cortex_prices.empty:
        return pd.DataFrame()
    cp = cortex_prices.copy()
    cp.columns = [str(c).upper() for c in cp.columns]
    need = {"FUNCTION_NAME", "MODEL_NAME", "CREDITS_PER_1M_TOKENS"}
    if not need.issubset(set(cp.columns)):
        return pd.DataFrame()
    cp["FUNCTION_NAME"] = cp["FUNCTION_NAME"].astype(str)
    cp["MODEL_NAME"] = cp["MODEL_NAME"].astype(str)
    cp["CREDITS_PER_1M_TOKENS"] = pd.to_numeric(cp["CREDITS_PER_1M_TOKENS"], errors="coerce")
    return cp.dropna(subset=["CREDITS_PER_1M_TOKENS"])


def switch_recommendations(
    usage: pd.DataFrame,
    cortex_prices: pd.DataFrame,
    credit_price: float,
    *,
    min_savings_pct: float = SWITCH_MIN_SAVINGS_PCT,
) -> list[Insight]:
    """Rank COMPLETE/embed switches where list rates imply material savings."""
    cp = _norm_prices(cortex_prices)
    if usage is None or usage.empty or cp.empty:
        return []

    u = usage.copy()
    u.columns = [str(c).upper() for c in u.columns]
    insights: list[Insight] = []

    for _, row in u.iterrows():
        tokens = float(row.get("TOKENS") or 0)
        actual = float(row.get("CREDITS") or 0)
        model = str(row.get("MODEL_NAME") or "")
        fn = str(row.get("FUNCTION_NAME") or "COMPLETE")
        if tokens <= 0 or actual <= 0 or not model:
            continue

        candidates = cp[cp["FUNCTION_NAME"].str.upper() == fn.upper()]
        if candidates.empty:
            continue

        best = None
        best_est = actual
        for _, alt in candidates.iterrows():
            alt_model = str(alt["MODEL_NAME"])
            if alt_model.lower() == model.lower():
                continue
            est = tokens / 1_000_000.0 * float(alt["CREDITS_PER_1M_TOKENS"])
            if est < best_est:
                best_est = est
                best = alt_model

        if best is None:
            continue
        saved = actual - best_est
        if saved / actual < min_savings_pct:
            continue
        usd = saved * credit_price
        insights.append(
            Insight(
                kind="switch",
                severity="high" if usd >= 50 or saved / actual >= 0.35 else "medium",
                headline=(
                    f"Switch {model} -> {best}: save ~{saved:,.2f} credits "
                    f"(~${usd:,.0f} est.) in this window"
                ),
                detail=(
                    f"Same {tokens:,.0f} tokens on {fn}. List-rate scenario only. "
                    f"validate quality/latency before changing production models. "
                    f"USD uses your entered $/credit (estimate, not an invoice)."
                ),
                savings_credits=round(saved, 4),
                savings_usd=round(usd, 2),
                meta={
                    "from_model": model,
                    "to_model": best,
                    "function": fn,
                    "tokens": tokens,
                    "your_credits": actual,
                    "alt_credits": round(best_est, 4),
                },
            )
        )

    insights.sort(key=lambda i: i.savings_usd, reverse=True)
    return insights


def concentration_insight(usage: pd.DataFrame, credit_price: float) -> Insight | None:
    if usage is None or usage.empty:
        return None
    u = usage.copy()
    u.columns = [str(c).upper() for c in u.columns]
    total = float(u["CREDITS"].sum())
    if total <= 0:
        return None
    top = u.sort_values("CREDITS", ascending=False).iloc[0]
    share = float(top["CREDITS"]) / total
    if share < CONCENTRATION_SHARE_PCT:
        return None
    model = str(top.get("MODEL_NAME") or "unknown")
    credits = float(top["CREDITS"])
    return Insight(
        kind="concentration",
        severity="medium" if share < 0.75 else "high",
        headline=f"{share:.0%} of Cortex credits on a single model ({model})",
        detail=(
            f"~{credits:,.2f} credits (~${credits * credit_price:,.0f} est.) concentrated "
            f"on {model} (threshold {CONCENTRATION_SHARE_PCT:.0%}). High concentration "
            f"increases cost risk if rates rise or quality needs shift. Review whether a "
            f"cheaper tier covers part of the workload."
        ),
        savings_credits=0.0,
        savings_usd=0.0,
        meta={"model": model, "share": share, "threshold": CONCENTRATION_SHARE_PCT},
    )


def anomaly_insights(spend: pd.DataFrame, credit_price: float) -> list[Insight]:
    if spend is None or spend.empty or "DAY" not in spend.columns:
        return []
    daily = spend.groupby("DAY", as_index=False)["CREDITS"].sum()
    if len(daily) < 7:
        return []
    med = float(daily["CREDITS"].median())
    if med <= 0:
        return []
    spikes = daily[daily["CREDITS"] >= med * SPIKE_MEDIAN_MULT].sort_values(
        "CREDITS", ascending=False
    )
    out: list[Insight] = []
    for _, row in spikes.head(3).iterrows():
        day = row["DAY"]
        credits = float(row["CREDITS"])
        usd = credits * credit_price
        out.append(
            Insight(
                kind="anomaly",
                severity="medium",
                headline=f"Spend spike on {pd.Timestamp(day).date()}: {credits:,.2f} credits",
                detail=(
                    f"~{credits / med:.1f}x your median daily Cortex credits "
                    f"(spike rule: >={SPIKE_MEDIAN_MULT:.1f}x median; ~${usd:,.0f} est.). "
                    f"Investigate batch jobs, eval loops, or unbounded COMPLETE calls that day."
                ),
                savings_credits=0.0,
                savings_usd=0.0,
                meta={
                    "day": str(pd.Timestamp(day).date()),
                    "credits": credits,
                    "median": med,
                    "threshold_mult": SPIKE_MEDIAN_MULT,
                },
            )
        )
    return out


def forecast_insight(
    spend: pd.DataFrame,
    credit_price: float,
    horizon_days: int = FORECAST_HORIZON_DAYS,
) -> Insight | None:
    if spend is None or spend.empty:
        return None
    daily = spend.groupby("DAY", as_index=False)["CREDITS"].sum().sort_values("DAY")
    if len(daily) < 7:
        return None
    trail = daily.tail(FORECAST_TRAIL_DAYS)
    avg = float(trail["CREDITS"].mean())
    projected = avg * horizon_days
    usd = projected * credit_price
    return Insight(
        kind="forecast",
        severity="info",
        headline=(
            f"Forward estimate: ~{projected:,.1f} Cortex credits "
            f"(~${usd:,.0f}) over next {horizon_days} days"
        ),
        detail=(
            f"Simple trailing {FORECAST_TRAIL_DAYS}-day average "
            f"({avg:,.2f} credits/day) x {horizon_days}. "
            f"Not ML forecasting. A planning number FinOps can challenge against budgets. "
            f"USD uses your entered $/credit."
        ),
        savings_credits=0.0,
        savings_usd=0.0,
        meta={
            "avg_daily_credits": avg,
            "horizon_days": horizon_days,
            "trail_days": FORECAST_TRAIL_DAYS,
            "projected_credits": projected,
        },
    )


def price_move_insights(
    usage: pd.DataFrame,
    llm_snapshot: pd.DataFrame,
    credit_price: float,
    *,
    limit: int | None = 5,
) -> list[Insight]:
    """Flag public list-price moves that overlap usage models (canonical id match)."""
    from model_ids import overlaps_used

    _ = credit_price  # reserved for future USD impact on list moves
    if usage is None or usage.empty or llm_snapshot is None or llm_snapshot.empty:
        return []
    u = usage.copy()
    u.columns = [str(c).upper() for c in u.columns]
    used = {str(m) for m in u.get("MODEL_NAME", pd.Series(dtype=str)).dropna().unique()}
    snap = llm_snapshot.copy()
    if "change_pct_90d" not in snap.columns:
        return []
    snap["change_pct_90d"] = pd.to_numeric(snap["change_pct_90d"], errors="coerce").fillna(0)
    moved = snap[snap["change_pct_90d"].abs() >= 5]
    out: list[Insight] = []
    for _, row in moved.iterrows():
        name = str(row.get("model_name") or row.get("MODEL_NAME") or "")
        pct = float(row.get("change_pct_90d") or 0)
        if not overlaps_used(name, used):
            continue
        direction = "dropped" if pct < 0 else "rose"
        out.append(
            Insight(
                kind="price",
                severity="info",
                headline=f"Public list price {direction} {abs(pct):.0f}% ({name})",
                detail=(
                    "From bundled / Marketplace price intelligence. "
                    "Overlaps models in your Cortex usage window. Revisit switch scenarios."
                ),
                meta={"model": name, "change_pct_90d": pct, "overlap": True},
            )
        )
    if limit is not None:
        return out[: int(limit)]
    return out


def build_advisor_pack(
    *,
    usage: pd.DataFrame,
    spend: pd.DataFrame,
    cortex_prices: pd.DataFrame,
    llm_snapshot: pd.DataFrame,
    credit_price: float,
    min_savings_pct: float = SWITCH_MIN_SAVINGS_PCT,
) -> dict[str, Any]:
    switches = switch_recommendations(
        usage, cortex_prices, credit_price, min_savings_pct=min_savings_pct
    )
    concentration = concentration_insight(usage, credit_price)
    anomalies = anomaly_insights(spend, credit_price)
    forecast = forecast_insight(spend, credit_price)
    prices = price_move_insights(usage, llm_snapshot, credit_price)

    # Prefer actionable $ savings over descriptive spikes/forecast.
    primary = switches[0] if switches else None
    if primary is None and concentration is not None:
        primary = concentration
    if primary is None and anomalies:
        primary = anomalies[0]
    if primary is None and forecast is not None:
        primary = forecast

    total_switch_usd = sum(i.savings_usd for i in switches)
    total_switch_credits = sum(i.savings_credits for i in switches)

    secondary: list[Insight] = []
    if concentration is not None and (primary is None or primary.kind != "concentration"):
        secondary.append(concentration)
    secondary.extend(anomalies)
    if forecast is not None and (primary is None or primary.kind != "forecast"):
        secondary.append(forecast)
    secondary.extend(prices)
    # remaining switches after primary
    if switches:
        secondary.extend(switches[1:4])

    return {
        "primary": primary,
        "switches": switches,
        "secondary": secondary,
        "total_switch_savings_usd": round(total_switch_usd, 2),
        "total_switch_savings_credits": round(total_switch_credits, 4),
    }
