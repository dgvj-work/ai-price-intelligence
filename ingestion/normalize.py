"""Unit normalization: USD, per-1M-tokens, per-GPU-hour."""

from __future__ import annotations

from datetime import UTC, datetime

from ingestion.models import (
    GpuPrice,
    ModelPriceSeed,
    NormalizedGpuPrice,
    NormalizedModelPrice,
    PriceUnit,
)


def tokens_to_per_1m(amount: float, unit: PriceUnit) -> float:
    """Convert a token price into USD per 1M tokens."""
    if unit == PriceUnit.PER_1M_TOKENS:
        return float(amount)
    if unit == PriceUnit.PER_1K_TOKENS:
        return float(amount) * 1000.0
    if unit == PriceUnit.PER_TOKEN:
        return float(amount) * 1_000_000.0
    raise ValueError(f"Cannot convert unit {unit} to per-1M-tokens")


def per_1m_to_unit(amount_per_1m: float, unit: PriceUnit) -> float:
    """Inverse conversion for round-trip tests."""
    if unit == PriceUnit.PER_1M_TOKENS:
        return float(amount_per_1m)
    if unit == PriceUnit.PER_1K_TOKENS:
        return float(amount_per_1m) / 1000.0
    if unit == PriceUnit.PER_TOKEN:
        return float(amount_per_1m) / 1_000_000.0
    raise ValueError(f"Cannot convert per-1M to unit {unit}")


def instance_hour_to_gpu_hour(price: float | None, gpu_count: int) -> float | None:
    if price is None:
        return None
    if gpu_count < 1:
        raise ValueError("gpu_count must be >= 1")
    return float(price) / float(gpu_count)


def normalize_model_price(seed: ModelPriceSeed) -> NormalizedModelPrice:
    retrieved = seed.retrieved_at or datetime.now(tz=UTC).replace(tzinfo=None)
    return NormalizedModelPrice(
        model_id=seed.model_id,
        price_input_usd_per_1m_tokens=tokens_to_per_1m(seed.price_input, seed.unit),
        price_output_usd_per_1m_tokens=tokens_to_per_1m(seed.price_output, seed.unit),
        price_cached_input_usd_per_1m_tokens=(
            tokens_to_per_1m(seed.price_cached_input, seed.unit)
            if seed.price_cached_input is not None
            else None
        ),
        batch_discount_pct=seed.batch_discount_pct,
        tier_notes=seed.tier_notes,
        source_url=str(seed.source_url),
        retrieved_at=retrieved.replace(tzinfo=None) if retrieved.tzinfo else retrieved,
    )


def normalize_gpu_price(price: GpuPrice, gpu_count: int) -> NormalizedGpuPrice:
    if price.prices_are_instance_hour:
        od = instance_hour_to_gpu_hour(price.price_on_demand_usd_hr, gpu_count)
        spot = instance_hour_to_gpu_hour(price.price_spot_usd_hr, gpu_count)
        reserved = instance_hour_to_gpu_hour(price.price_1yr_reserved_usd_hr, gpu_count)
    else:
        od = price.price_on_demand_usd_hr
        spot = price.price_spot_usd_hr
        reserved = price.price_1yr_reserved_usd_hr

    retrieved = price.retrieved_at
    if retrieved.tzinfo is not None:
        retrieved = retrieved.replace(tzinfo=None)

    return NormalizedGpuPrice(
        instance_id=price.instance_id,
        region=price.region,
        price_on_demand_usd_hr=od,
        price_spot_usd_hr=spot,
        price_1yr_reserved_usd_hr=reserved,
        source_url=str(price.source_url),
        retrieved_at=retrieved,
    )
