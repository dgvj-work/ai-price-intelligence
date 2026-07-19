"""AWS Price List API (public, no auth) — GPU instance families."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from ingestion.models import GpuInstance, GpuPrice

logger = logging.getLogger(__name__)

AWS_OFFER_INDEX = "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/index.json"
SOURCE_URL = "https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/price-changes.html"

GPU_KEYWORDS = ("H100", "A100", "L4", "L40", "V100", "T4", "A10G", "A10", "GPU")
# Common GPU instance families / types of interest
INSTANCE_PREFIXES = ("p3", "p4", "p5", "g4", "g5", "g6", "inf1", "inf2")


@retry(stop=stop_after_attempt(4), wait=wait_exponential_jitter(initial=1, max=20))
def _get_json(client: httpx.Client, url: str) -> dict[str, Any]:
    resp = client.get(url, timeout=60.0)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise TypeError(f"Expected JSON object from {url}")
    return data


def _is_gpu_product(attrs: dict[str, str]) -> bool:
    instance_type = attrs.get("instanceType", "").lower()
    gpu = attrs.get("gpu", "0")
    if instance_type.startswith(INSTANCE_PREFIXES):
        return True
    try:
        if float(gpu) > 0:
            return True
    except ValueError:
        pass
    blob = " ".join(attrs.values()).upper()
    return any(k in blob for k in GPU_KEYWORDS)


def fetch_aws_gpu_pricing(
    *,
    regions: list[str] | None = None,
    client: httpx.Client | None = None,
) -> tuple[list[GpuInstance], list[GpuPrice]]:
    """Fetch On-Demand EC2 GPU pricing for selected regions (default us-east-1)."""
    regions = regions or ["us-east-1"]
    owned = client is None
    client = client or httpx.Client(headers={"User-Agent": "ai-price-intelligence/0.1"})
    retrieved = datetime.now(tz=UTC).replace(tzinfo=None)
    instances: dict[str, GpuInstance] = {}
    prices: list[GpuPrice] = []

    try:
        index = _get_json(client, AWS_OFFER_INDEX)
        ec2_current = index["offers"]["AmazonEC2"]["currentVersionUrl"]
        # currentVersionUrl is relative like /offers/v1.0/aws/AmazonEC2/..../index.json
        offer_url = "https://pricing.us-east-1.amazonaws.com" + ec2_current
        # Prefer region index for smaller downloads
        # Fall back to full offer if region file missing.
        for region in regions:
            region_url = offer_url.replace("/index.json", "/region_index.json")
            try:
                region_index = _get_json(client, region_url)
                # structure varies; try regions -> regionCurrentVersionUrl
                regions_map = region_index.get("regions", {})
                rel = regions_map.get(region, {}).get("currentVersionUrl")
                url = "https://pricing.us-east-1.amazonaws.com" + rel if rel else offer_url
            except Exception:  # noqa: BLE001 — polite fallback
                url = offer_url

            logger.info("Fetching AWS EC2 prices from %s", url)
            offer = _get_json(client, url)
            products = offer.get("products", {})
            terms = offer.get("terms", {}).get("OnDemand", {})

            for sku, product in products.items():
                attrs = product.get("attributes", {})
                family = product.get("productFamily")
                known_family = family in {
                    "Compute Instance",
                    "GPU instance",
                    "Compute Instance (bare metal)",
                }
                if not known_family and not _is_gpu_product(attrs):
                    continue
                if not _is_gpu_product(attrs):
                    continue
                if attrs.get("operatingSystem", "Linux") != "Linux":
                    continue
                if attrs.get("tenancy", "Shared") not in {"Shared", "shared"}:
                    continue
                if attrs.get("preInstalledSw", "NA") not in {"NA", "NA "}:
                    continue
                if attrs.get("capacitystatus", "Used") not in {"Used", "used"}:
                    continue

                instance_name = attrs.get("instanceType")
                if not instance_name:
                    continue
                region_code = attrs.get("regionCode") or region
                gpu_count = int(float(attrs.get("gpu", "1") or "1"))
                gpu_model = attrs.get("gpuMemory") or attrs.get("physicalProcessor") or "GPU"
                # Better label from instance family heuristics
                upper_name = instance_name.upper()
                for kw in GPU_KEYWORDS:
                    if kw in upper_name or kw in str(attrs.get("gpuMemory", "")).upper():
                        gpu_model = kw
                        break

                instance_id = f"aws:{instance_name}"
                instances[instance_id] = GpuInstance(
                    instance_id=instance_id,
                    cloud="aws",
                    instance_name=instance_name,
                    gpu_model=str(gpu_model),
                    gpu_count=max(gpu_count, 1),
                    vram_gb=None,
                    region_scope="regional",
                )

                sku_terms = terms.get(sku, {})
                on_demand: float | None = None
                for _term_id, term in sku_terms.items():
                    for dim in term.get("priceDimensions", {}).values():
                        usd = dim.get("pricePerUnit", {}).get("USD")
                        if usd is not None:
                            on_demand = float(usd)
                            break
                if on_demand is None:
                    continue
                prices.append(
                    GpuPrice(
                        instance_id=instance_id,
                        region=region_code,
                        price_on_demand_usd_hr=on_demand,
                        price_spot_usd_hr=None,
                        price_1yr_reserved_usd_hr=None,
                        source_url=SOURCE_URL,
                        retrieved_at=retrieved,
                        prices_are_instance_hour=True,
                    )
                )
    finally:
        if owned:
            client.close()

    logger.info("AWS: %d instances, %d price rows", len(instances), len(prices))
    return list(instances.values()), prices
