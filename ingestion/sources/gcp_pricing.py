"""GCP GPU pricing via public Cloud Billing SKU catalog endpoint."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from ingestion.models import GpuInstance, GpuPrice

logger = logging.getLogger(__name__)

# Public Cloud Billing Catalog (API key optional for limited use; we call without key first).
SKU_URL = "https://cloudbilling.googleapis.com/v1/services/6F81-5844-456A/skus"
SOURCE_URL = "https://cloud.google.com/products/calculator"

GPU_HINTS = ("GPU", "NVIDIA", "H100", "A100", "L4", "L40", "T4", "V100", "A10")


@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=15))
def _get(client: httpx.Client, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    resp = client.get(url, params=params, timeout=60.0)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise TypeError("Expected JSON object")
    return data


def fetch_gcp_gpu_pricing(
    *,
    client: httpx.Client | None = None,
    max_pages: int = 30,
) -> tuple[list[GpuInstance], list[GpuPrice]]:
    """Best-effort GCP GPU SKU pull. Returns empty on auth/network failures."""
    owned = client is None
    client = client or httpx.Client(headers={"User-Agent": "ai-price-intelligence/0.1"})
    retrieved = datetime.now(tz=UTC).replace(tzinfo=None)
    instances: dict[str, GpuInstance] = {}
    prices: list[GpuPrice] = []
    page_token: str | None = None
    pages = 0

    try:
        while pages < max_pages:
            pages += 1
            params: dict[str, Any] = {"pageSize": 5000}
            if page_token:
                params["pageToken"] = page_token
            try:
                payload = _get(client, SKU_URL, params=params)
            except Exception as exc:  # noqa: BLE001
                logger.warning("GCP pricing unavailable (%s); continuing without GCP rows", exc)
                return [], []

            for sku in payload.get("skus", []):
                desc = str(sku.get("description", ""))
                upper = desc.upper()
                if not any(h in upper for h in GPU_HINTS):
                    continue
                category = sku.get("category", {})
                if category.get("resourceFamily") not in {"Compute", None}:
                    continue
                sku_id = sku.get("skuId") or desc
                instance_id = f"gcp:{sku_id}"
                gpu_model = "GPU"
                for h in ("H100", "A100", "L40S", "L40", "L4", "V100", "T4", "A10"):
                    if h in upper:
                        gpu_model = h
                        break
                instances[instance_id] = GpuInstance(
                    instance_id=instance_id,
                    cloud="gcp",
                    instance_name=desc[:200],
                    gpu_model=gpu_model,
                    gpu_count=1,
                    vram_gb=None,
                    region_scope="regional",
                )
                for region in sku.get("serviceRegions", ["global"])[:5]:
                    pricing_info = sku.get("pricingInfo") or []
                    amount: float | None = None
                    if pricing_info:
                        pricing_expr = pricing_info[0].get("pricingExpression", {})
                        tiers = pricing_expr.get("tieredRates") or []
                        if tiers:
                            unit_price = tiers[0].get("unitPrice", {})
                            nanos = int(unit_price.get("nanos") or 0)
                            units = int(unit_price.get("units") or 0)
                            amount = units + nanos / 1_000_000_000
                    if amount is None:
                        continue
                    prices.append(
                        GpuPrice(
                            instance_id=instance_id,
                            region=str(region),
                            price_on_demand_usd_hr=amount,
                            price_spot_usd_hr=None,
                            price_1yr_reserved_usd_hr=None,
                            source_url=SOURCE_URL,
                            retrieved_at=retrieved,
                            # GPU attachment SKUs are often already per GPU-hour
                            prices_are_instance_hour=False,
                        )
                    )
            page_token = payload.get("nextPageToken")
            if not page_token:
                break
    finally:
        if owned:
            client.close()

    logger.info("GCP: %d instances, %d price rows", len(instances), len(prices))
    return list(instances.values()), prices
