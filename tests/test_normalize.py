"""Round-trip and unit tests for normalize.py (≥85% coverage target)."""

from __future__ import annotations

from datetime import datetime

import pytest
from ingestion.models import GpuPrice, ModelPriceSeed, PriceUnit
from ingestion.normalize import (
    instance_hour_to_gpu_hour,
    normalize_gpu_price,
    normalize_model_price,
    per_1m_to_unit,
    tokens_to_per_1m,
)


@pytest.mark.parametrize(
    ("amount", "unit", "expected"),
    [
        (2.5, PriceUnit.PER_1M_TOKENS, 2.5),
        (0.0025, PriceUnit.PER_1K_TOKENS, 2.5),
        (0.0000025, PriceUnit.PER_TOKEN, 2.5),
    ],
)
def test_tokens_to_per_1m(amount: float, unit: PriceUnit, expected: float) -> None:
    assert tokens_to_per_1m(amount, unit) == pytest.approx(expected)


@pytest.mark.parametrize(
    "unit",
    [PriceUnit.PER_1M_TOKENS, PriceUnit.PER_1K_TOKENS, PriceUnit.PER_TOKEN],
)
def test_round_trip_token_units(unit: PriceUnit) -> None:
    original = 3.141592
    per_1m = tokens_to_per_1m(original, unit)
    back = per_1m_to_unit(per_1m, unit)
    assert back == pytest.approx(original)


def test_rejects_non_token_unit() -> None:
    with pytest.raises(ValueError):
        tokens_to_per_1m(1.0, PriceUnit.USD_PER_GPU_HOUR)
    with pytest.raises(ValueError):
        per_1m_to_unit(1.0, PriceUnit.CREDITS_PER_1M_TOKENS)


def test_instance_hour_to_gpu_hour() -> None:
    assert instance_hour_to_gpu_hour(98.32, 8) == pytest.approx(12.29)
    assert instance_hour_to_gpu_hour(None, 8) is None
    with pytest.raises(ValueError):
        instance_hour_to_gpu_hour(1.0, 0)


def test_normalize_model_price() -> None:
    seed = ModelPriceSeed(
        model_id="openai:gpt-4o",
        unit=PriceUnit.PER_1K_TOKENS,
        price_input=0.0025,
        price_output=0.01,
        price_cached_input=0.00125,
        source_url="https://openai.com/api/pricing/",
        retrieved_at=datetime(2026, 7, 1),
    )
    norm = normalize_model_price(seed)
    assert norm.price_input_usd_per_1m_tokens == pytest.approx(2.5)
    assert norm.price_output_usd_per_1m_tokens == pytest.approx(10.0)
    assert norm.price_cached_input_usd_per_1m_tokens == pytest.approx(1.25)


def test_normalize_gpu_price_instance_hour() -> None:
    price = GpuPrice(
        instance_id="aws:p5.48xlarge",
        region="us-east-1",
        price_on_demand_usd_hr=98.32,
        price_spot_usd_hr=40.0,
        price_1yr_reserved_usd_hr=60.0,
        source_url="https://aws.amazon.com/ec2/pricing/",
        retrieved_at=datetime(2026, 7, 1),
        prices_are_instance_hour=True,
    )
    norm = normalize_gpu_price(price, gpu_count=8)
    assert norm.price_on_demand_usd_hr == pytest.approx(12.29)
    assert norm.price_spot_usd_hr == pytest.approx(5.0)


def test_normalize_gpu_price_already_gpu_hour() -> None:
    price = GpuPrice(
        instance_id="gcp:gpu",
        region="us-central1",
        price_on_demand_usd_hr=3.5,
        source_url="https://cloud.google.com/",
        retrieved_at=datetime(2026, 7, 1),
        prices_are_instance_hour=False,
    )
    norm = normalize_gpu_price(price, gpu_count=8)
    assert norm.price_on_demand_usd_hr == pytest.approx(3.5)
