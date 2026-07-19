"""Azure Retail Prices API (public REST, no auth) — GPU VMs."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from ingestion.models import GpuInstance, GpuPrice

logger = logging.getLogger(__name__)

BASE = "https://prices.azure.com/api/retail/prices"
SOURCE_URL = "https://prices.azure.com/api/retail/prices"

GPU_SKU_HINTS = ("NC", "ND", "NG", "NV", "H100", "A100", "V100", "T4", "A10", "L4", "L40")

# Common Azure N-series GPU counts by SKU family prefix
_GPU_COUNT_BY_PREFIX: dict[str, int] = {
    "Standard_NC6": 1,
    "Standard_NC12": 2,
    "Standard_NC24": 4,
    "Standard_NC24rs": 4,
    "Standard_NC4as_T4_v3": 1,
    "Standard_NC8as_T4_v3": 1,
    "Standard_NC16as_T4_v3": 1,
    "Standard_NC64as_T4_v3": 4,
    "Standard_ND40rs_v2": 8,
    "Standard_ND96asr_v4": 8,
    "Standard_ND96amsr_A100_v4": 8,
    "Standard_ND96isr_H100_v5": 8,
    "Standard_NC24ads_A100_v4": 1,
    "Standard_NC48ads_A100_v4": 2,
    "Standard_NC96ads_A100_v4": 4,
}


def _infer_gpu_count(sku: str, product: str) -> int:
    # Longest prefix first so NC24ads wins over NC24
    for prefix, count in sorted(_GPU_COUNT_BY_PREFIX.items(), key=lambda kv: -len(kv[0])):
        if sku.startswith(prefix) or sku == prefix:
            return count
    blob = f"{sku} {product}".upper()
    # Heuristic: "8x" / "x8" style markers
    for n in (8, 4, 2):
        if f"{n}X" in blob or f"X{n}" in blob or f"{n} GPU" in blob:
            return n
    return 1


@retry(stop=stop_after_attempt(4), wait=wait_exponential_jitter(initial=1, max=20))
def _get(client: httpx.Client, url: str) -> dict[str, Any]:
    resp = client.get(url, timeout=60.0)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise TypeError("Expected JSON object")
    return data


def _looks_like_gpu(item: dict[str, Any]) -> bool:
    blob = " ".join(
        str(item.get(k, ""))
        for k in ("armSkuName", "productName", "skuName", "meterName", "serviceName")
    ).upper()
    if "VIRTUAL MACHINES" not in blob and item.get("serviceName") != "Virtual Machines":
        return False
    return any(h in blob for h in GPU_SKU_HINTS)


def fetch_azure_gpu_pricing(
    *,
    currency: str = "USD",
    client: httpx.Client | None = None,
    max_pages: int = 40,
) -> tuple[list[GpuInstance], list[GpuPrice]]:
    owned = client is None
    client = client or httpx.Client(headers={"User-Agent": "ai-price-intelligence/0.1"})
    retrieved = datetime.now(tz=UTC).replace(tzinfo=None)
    filt = (
        "serviceName eq 'Virtual Machines' and priceType eq 'Consumption' "
        f"and currencyCode eq '{currency}'"
    )
    url: str | None = f"{BASE}?$filter={quote(filt)}"
    instances: dict[str, GpuInstance] = {}
    prices: list[GpuPrice] = []
    pages = 0

    try:
        while url and pages < max_pages:
            pages += 1
            payload = _get(client, url)
            for item in payload.get("Items", []):
                if not _looks_like_gpu(item):
                    continue
                # Skip Windows / low-priority duplicates when possible
                sku = str(item.get("armSkuName") or item.get("skuName") or "")
                if not sku:
                    continue
                product = str(item.get("productName") or "")
                if "Windows" in product:
                    continue
                region = str(item.get("armRegionName") or item.get("location") or "unknown")
                retail = item.get("retailPrice")
                if retail is None:
                    continue
                instance_id = f"azure:{sku}"
                gpu_model = "GPU"
                for h in ("H100", "A100", "L40", "L4", "V100", "T4", "A10"):
                    if h in product.upper() or h in sku.upper():
                        gpu_model = h
                        break
                gpu_count = _infer_gpu_count(sku, product)
                instances[instance_id] = GpuInstance(
                    instance_id=instance_id,
                    cloud="azure",
                    instance_name=sku,
                    gpu_model=gpu_model,
                    gpu_count=gpu_count,
                    vram_gb=None,
                    region_scope="regional",
                )
                prices.append(
                    GpuPrice(
                        instance_id=instance_id,
                        region=region,
                        price_on_demand_usd_hr=float(retail),
                        price_spot_usd_hr=None,
                        price_1yr_reserved_usd_hr=None,
                        source_url=SOURCE_URL,
                        retrieved_at=retrieved,
                        prices_are_instance_hour=True,
                    )
                )
            url = payload.get("NextPageLink")
            if url:
                # polite pacing between pages
                import time

                time.sleep(0.2)
    finally:
        if owned:
            client.close()

    logger.info("Azure: %d instances, %d price rows (%d pages)", len(instances), len(prices), pages)
    return list(instances.values()), prices
