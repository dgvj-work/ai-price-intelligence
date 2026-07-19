"""Seed YAML validation tests."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from ingestion.models import ModelPriceSeed, PriceUnit
from ingestion.sources.seed_loader import SEEDS_DIR, load_seed_bundle
from pydantic import ValidationError


def test_load_real_seeds() -> None:
    bundle = load_seed_bundle(SEEDS_DIR)
    assert len(bundle.providers) >= 9
    assert len(bundle.models) >= 20
    assert len(bundle.model_prices) >= 20
    assert len(bundle.benchmarks) >= 15
    assert len(bundle.cortex_prices) >= 12
    assert len(bundle.gpu_instances) >= 4
    assert len(bundle.gpu_prices) >= 4
    model_ids = {m.model_id for m in bundle.models}
    for p in bundle.model_prices:
        assert p.model_id in model_ids
        assert float(p.price_input) >= 0
        assert float(p.price_output) >= 0
    gpu_ids = {g.instance_id for g in bundle.gpu_instances}
    for gp in bundle.gpu_prices:
        assert gp.instance_id in gpu_ids


def test_reject_negative_price() -> None:
    with pytest.raises(ValidationError):
        ModelPriceSeed(
            model_id="x",
            unit=PriceUnit.PER_1M_TOKENS,
            price_input=-1,
            price_output=1,
            source_url="https://example.com",
            retrieved_at=datetime(2026, 1, 1),
        )


def test_reject_bad_unit_for_llm() -> None:
    with pytest.raises(ValidationError):
        ModelPriceSeed(
            model_id="x",
            unit=PriceUnit.USD_PER_GPU_HOUR,
            price_input=1,
            price_output=1,
            source_url="https://example.com",
        )


def test_seeds_dir_exists() -> None:
    assert Path(SEEDS_DIR).is_dir()
