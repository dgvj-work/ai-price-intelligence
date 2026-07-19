"""Orchestrator CLI: `python -m ingestion.run_refresh`."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

import click

from ingestion.load_snowflake import load_to_snowflake, write_parquet_bundle
from ingestion.models import NormalizedGpuPrice
from ingestion.normalize import normalize_gpu_price, normalize_model_price
from ingestion.sources.aws_pricing import fetch_aws_gpu_pricing
from ingestion.sources.azure_pricing import fetch_azure_gpu_pricing
from ingestion.sources.gcp_pricing import fetch_gcp_gpu_pricing
from ingestion.sources.hf_leaderboards import fetch_hf_benchmark_hints
from ingestion.sources.seed_loader import load_seed_bundle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("ingestion.run_refresh")


@click.command()
@click.option("--dry-run", is_flag=True, help="No Snowflake; write parquet to /tmp")
@click.option("--skip-cloud", is_flag=True, help="Skip AWS/Azure/GCP API pulls")
@click.option("--skip-hf", is_flag=True, help="Skip optional Hugging Face enrichment")
@click.option(
    "--out-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Dry-run output directory (default /tmp/ai_price_intel/<run_id>)",
)
def main(dry_run: bool, skip_cloud: bool, skip_hf: bool, out_dir: Path | None) -> None:
    """Weekly refresh: seeds + cloud GPU APIs → CURATED (or parquet)."""
    started = datetime.now(tz=UTC).replace(tzinfo=None)
    refresh_id = str(uuid.uuid4())
    logger.info("Starting refresh %s (dry_run=%s)", refresh_id, dry_run)

    try:
        bundle = load_seed_bundle()
        model_prices = [normalize_model_price(p) for p in bundle.model_prices]

        # Seed GPU rows as baseline; cloud APIs override matching instance_ids.
        seed_inst_map = {i.instance_id: i for i in bundle.gpu_instances}
        gpu_price_map: dict[str, NormalizedGpuPrice] = {}
        for price in bundle.gpu_prices:
            inst = seed_inst_map.get(price.instance_id)
            if inst is None:
                continue
            key = f"{price.instance_id}|{price.region}"
            gpu_price_map[key] = normalize_gpu_price(price, inst.gpu_count)

        if not skip_cloud:
            try:
                aws_i, aws_p = fetch_aws_gpu_pricing()
                aws_by_id = {i.instance_id: i for i in aws_i}
                seed_inst_map.update(aws_by_id)
                for price in aws_p:
                    inst = aws_by_id.get(price.instance_id)
                    if inst is None:
                        continue
                    key = f"{price.instance_id}|{price.region}"
                    gpu_price_map[key] = normalize_gpu_price(price, inst.gpu_count)
            except Exception as exc:  # noqa: BLE001
                logger.warning("AWS pricing failed: %s", exc)

            try:
                az_i, az_p = fetch_azure_gpu_pricing()
                az_by_id = {i.instance_id: i for i in az_i}
                seed_inst_map.update(az_by_id)
                for price in az_p:
                    inst = az_by_id[price.instance_id]
                    key = f"{price.instance_id}|{price.region}"
                    gpu_price_map[key] = normalize_gpu_price(price, inst.gpu_count)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Azure pricing failed: %s", exc)

            try:
                gcp_i, gcp_p = fetch_gcp_gpu_pricing()
                gcp_by_id = {i.instance_id: i for i in gcp_i}
                seed_inst_map.update(gcp_by_id)
                for price in gcp_p:
                    inst = gcp_by_id[price.instance_id]
                    key = f"{price.instance_id}|{price.region}"
                    gpu_price_map[key] = normalize_gpu_price(price, inst.gpu_count)
            except Exception as exc:  # noqa: BLE001
                logger.warning("GCP pricing failed: %s", exc)
        else:
            logger.info("Skipping cloud GPU APIs (--skip-cloud); using GPU seed fallback")

        gpu_instances = list(seed_inst_map.values())
        gpu_prices_norm = list(gpu_price_map.values())

        benchmarks = list(bundle.benchmarks)
        if not skip_hf:
            name_map = {m.model_name: m.model_id for m in bundle.models}
            benchmarks.extend(fetch_hf_benchmark_hints(model_name_to_id=name_map))
        else:
            logger.info("Skipping HF enrichment (--skip-hf)")

        if dry_run:
            target = out_dir or Path(f"/tmp/ai_price_intel/{refresh_id}")
            write_parquet_bundle(
                target,
                providers=bundle.providers,
                models=bundle.models,
                model_prices=model_prices,
                benchmarks=benchmarks,
                cortex=bundle.cortex_prices,
                gpu_instances=gpu_instances,
                gpu_prices=gpu_prices_norm,
            )
            logger.info("Dry-run complete → %s", target)
            return

        counts = load_to_snowflake(
            refresh_id=refresh_id,
            started_at=started,
            providers=bundle.providers,
            models=bundle.models,
            model_prices=model_prices,
            benchmarks=benchmarks,
            cortex=bundle.cortex_prices,
            gpu_instances=gpu_instances,
            gpu_prices=gpu_prices_norm,
            as_of=started,
        )
        logger.info("Refresh SUCCESS counts=%s", counts)
    except Exception as exc:  # noqa: BLE001
        logger.error("Refresh FAILED: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
