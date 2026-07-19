"""Load + validate YAML seeds against pydantic models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ingestion.models import (
    BenchmarkSeed,
    CortexPriceSeed,
    GpuInstance,
    GpuPrice,
    ModelPriceSeed,
    ModelRecord,
    Provider,
    SeedBundle,
)

SEEDS_DIR = Path(__file__).resolve().parent / "seeds"


def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_seed_bundle(seeds_dir: Path | None = None) -> SeedBundle:
    root = seeds_dir or SEEDS_DIR
    try:
        providers_raw = _load_yaml(root / "llm_models.yaml")
        pricing_raw = _load_yaml(root / "llm_pricing.yaml")
        benchmarks_raw = _load_yaml(root / "benchmarks.yaml")
        cortex_raw = _load_yaml(root / "cortex_pricing.yaml")
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing seed file: {exc}") from exc

    gpu_raw: dict[str, Any] = {}
    gpu_path = root / "gpu_instances.yaml"
    if gpu_path.exists():
        gpu_raw = _load_yaml(gpu_path) or {}

    providers = [Provider.model_validate(p) for p in providers_raw.get("providers", [])]
    models = [ModelRecord.model_validate(m) for m in providers_raw.get("models", [])]
    model_prices = [ModelPriceSeed.model_validate(p) for p in pricing_raw.get("prices", [])]
    benchmarks = [BenchmarkSeed.model_validate(b) for b in benchmarks_raw.get("benchmarks", [])]
    cortex_prices = [CortexPriceSeed.model_validate(c) for c in cortex_raw.get("cortex_prices", [])]
    gpu_instances = [GpuInstance.model_validate(g) for g in gpu_raw.get("instances", [])]
    gpu_prices = [GpuPrice.model_validate(p) for p in gpu_raw.get("prices", [])]

    provider_ids = {p.provider_id for p in providers}
    model_ids = {m.model_id for m in models}
    gpu_ids = {g.instance_id for g in gpu_instances}

    errors: list[str] = []
    for m in models:
        if m.provider_id not in provider_ids:
            errors.append(f"model {m.model_id} references unknown provider {m.provider_id}")
    for mp in model_prices:
        if mp.model_id not in model_ids:
            errors.append(f"price references unknown model_id {mp.model_id}")
    for b in benchmarks:
        if b.model_id not in model_ids:
            errors.append(f"benchmark references unknown model_id {b.model_id}")
    for gp in gpu_prices:
        if gp.instance_id not in gpu_ids:
            errors.append(f"gpu price references unknown instance_id {gp.instance_id}")

    if errors:
        raise ValueError("Seed validation failed: " + "; ".join(errors))

    return SeedBundle(
        providers=providers,
        models=models,
        model_prices=model_prices,
        benchmarks=benchmarks,
        cortex_prices=cortex_prices,
        gpu_instances=gpu_instances,
        gpu_prices=gpu_prices,
    )
