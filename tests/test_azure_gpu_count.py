"""Azure GPU count inference."""

from __future__ import annotations

from ingestion.sources.azure_pricing import _infer_gpu_count


def test_known_prefixes() -> None:
    assert _infer_gpu_count("Standard_ND96isr_H100_v5", "") == 8
    assert _infer_gpu_count("Standard_NC24ads_A100_v4", "") == 1
    assert _infer_gpu_count("Standard_NC96ads_A100_v4", "") == 4


def test_heuristic_fallback() -> None:
    assert _infer_gpu_count("Custom_SKU", "8x NVIDIA H100") == 8
    assert _infer_gpu_count("Unknown", "Linux") == 1
