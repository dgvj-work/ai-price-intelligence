"""Write RAW tables and MERGE into CURATED (SCD2 for price histories)."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ingestion.models import (
    BenchmarkSeed,
    CortexPriceSeed,
    GpuInstance,
    ModelRecord,
    NormalizedGpuPrice,
    NormalizedModelPrice,
    Provider,
)
from ingestion.scd2 import (
    Scd2Row,
    cortex_price_hash,
    gpu_price_hash,
    merge_scd2,
    model_price_hash,
)

logger = logging.getLogger(__name__)

QUALITY_SQL = Path(__file__).resolve().parents[1] / "warehouse" / "sql" / "04_quality_checks.sql"


def write_parquet_bundle(
    out_dir: Path,
    *,
    providers: list[Provider],
    models: list[ModelRecord],
    model_prices: list[NormalizedModelPrice],
    benchmarks: list[BenchmarkSeed],
    cortex: list[CortexPriceSeed],
    gpu_instances: list[GpuInstance],
    gpu_prices: list[NormalizedGpuPrice],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([p.model_dump(mode="json") for p in providers]).to_parquet(
        out_dir / "dim_provider.parquet", index=False
    )
    pd.DataFrame([m.model_dump(mode="json") for m in models]).to_parquet(
        out_dir / "dim_model.parquet", index=False
    )
    pd.DataFrame([p.model_dump(mode="json") for p in model_prices]).to_parquet(
        out_dir / "fact_model_price.parquet", index=False
    )
    pd.DataFrame([b.model_dump(mode="json") for b in benchmarks]).to_parquet(
        out_dir / "fact_benchmark.parquet", index=False
    )
    pd.DataFrame([c.model_dump(mode="json") for c in cortex]).to_parquet(
        out_dir / "fact_cortex_price.parquet", index=False
    )
    pd.DataFrame([g.model_dump(mode="json") for g in gpu_instances]).to_parquet(
        out_dir / "dim_gpu_instance.parquet", index=False
    )
    pd.DataFrame([g.model_dump(mode="json") for g in gpu_prices]).to_parquet(
        out_dir / "fact_gpu_price.parquet", index=False
    )
    logger.info("Wrote parquet bundle to %s", out_dir)


def connect_snowflake() -> Any:
    import snowflake.connector
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization

    private_key_path = os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]
    passphrase = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")
    with open(private_key_path, "rb") as f:
        p_key = serialization.load_pem_private_key(
            f.read(),
            password=passphrase.encode() if passphrase else None,
            backend=default_backend(),
        )
    pkb = p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        private_key=pkb,
        role=os.environ.get("SNOWFLAKE_ROLE", "AI_PRICE_ADMIN"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "AI_PRICE_INTEL"),
    )


def _exec_many(cur: Any, sql: str, rows: list[tuple[Any, ...]]) -> None:
    if not rows:
        return
    cur.executemany(sql, rows)


def load_to_snowflake(
    *,
    refresh_id: str,
    started_at: datetime,
    providers: list[Provider],
    models: list[ModelRecord],
    model_prices: list[NormalizedModelPrice],
    benchmarks: list[BenchmarkSeed],
    cortex: list[CortexPriceSeed],
    gpu_instances: list[GpuInstance],
    gpu_prices: list[NormalizedGpuPrice],
    as_of: datetime,
) -> dict[str, int]:
    conn = connect_snowflake()
    counts: dict[str, int] = {}
    try:
        cur = conn.cursor()
        cur.execute("USE DATABASE AI_PRICE_INTEL")

        # Stage RAW
        cur.execute("DELETE FROM RAW.DIM_PROVIDER")
        _exec_many(
            cur,
            "INSERT INTO RAW.DIM_PROVIDER (PROVIDER_ID, NAME, TYPE, WEBSITE, BATCH_ID) "
            "VALUES (%s,%s,%s,%s,%s)",
            [
                (
                    p.provider_id,
                    p.name,
                    p.type.value,
                    str(p.website) if p.website else None,
                    refresh_id,
                )
                for p in providers
            ],
        )
        counts["raw_providers"] = len(providers)

        cur.execute("DELETE FROM RAW.DIM_MODEL")
        _exec_many(
            cur,
            "INSERT INTO RAW.DIM_MODEL ("
            "MODEL_ID, PROVIDER_ID, MODEL_NAME, FAMILY, MODALITY, CONTEXT_WINDOW_TOKENS, "
            "MAX_OUTPUT_TOKENS, SUPPORTS_TOOLS, SUPPORTS_VISION, LICENSE, RELEASE_DATE, "
            "DEPRECATION_DATE, IS_ACTIVE, BATCH_ID) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            [
                (
                    m.model_id,
                    m.provider_id,
                    m.model_name,
                    m.family,
                    m.modality.value,
                    m.context_window_tokens,
                    m.max_output_tokens,
                    m.supports_tools,
                    m.supports_vision,
                    m.license.value,
                    m.release_date,
                    m.deprecation_date,
                    m.is_active,
                    refresh_id,
                )
                for m in models
            ],
        )
        counts["raw_models"] = len(models)

        # Upsert dims
        cur.execute(
            """
            MERGE INTO CURATED.DIM_PROVIDER t
            USING RAW.DIM_PROVIDER s ON t.PROVIDER_ID = s.PROVIDER_ID
            WHEN MATCHED THEN UPDATE SET
              NAME = s.NAME, TYPE = s.TYPE, WEBSITE = s.WEBSITE, UPDATED_AT = CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN INSERT (PROVIDER_ID, NAME, TYPE, WEBSITE)
              VALUES (s.PROVIDER_ID, s.NAME, s.TYPE, s.WEBSITE)
            """
        )
        cur.execute(
            """
            MERGE INTO CURATED.DIM_MODEL t
            USING RAW.DIM_MODEL s ON t.MODEL_ID = s.MODEL_ID
            WHEN MATCHED THEN UPDATE SET
              PROVIDER_ID=s.PROVIDER_ID, MODEL_NAME=s.MODEL_NAME, FAMILY=s.FAMILY,
              MODALITY=s.MODALITY, CONTEXT_WINDOW_TOKENS=s.CONTEXT_WINDOW_TOKENS,
              MAX_OUTPUT_TOKENS=s.MAX_OUTPUT_TOKENS, SUPPORTS_TOOLS=s.SUPPORTS_TOOLS,
              SUPPORTS_VISION=s.SUPPORTS_VISION, LICENSE=s.LICENSE,
              RELEASE_DATE=s.RELEASE_DATE, DEPRECATION_DATE=s.DEPRECATION_DATE,
              IS_ACTIVE=s.IS_ACTIVE, UPDATED_AT=CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN INSERT (
              MODEL_ID, PROVIDER_ID, MODEL_NAME, FAMILY, MODALITY, CONTEXT_WINDOW_TOKENS,
              MAX_OUTPUT_TOKENS, SUPPORTS_TOOLS, SUPPORTS_VISION, LICENSE, RELEASE_DATE,
              DEPRECATION_DATE, IS_ACTIVE
            ) VALUES (
              s.MODEL_ID, s.PROVIDER_ID, s.MODEL_NAME, s.FAMILY, s.MODALITY,
              s.CONTEXT_WINDOW_TOKENS, s.MAX_OUTPUT_TOKENS, s.SUPPORTS_TOOLS,
              s.SUPPORTS_VISION, s.LICENSE, s.RELEASE_DATE, s.DEPRECATION_DATE, s.IS_ACTIVE
            )
            """
        )

        # SCD2 model prices
        cur.execute(
            "SELECT MODEL_ID, PRICE_INPUT_USD_PER_1M_TOKENS, PRICE_OUTPUT_USD_PER_1M_TOKENS, "
            "PRICE_CACHED_INPUT_USD_PER_1M_TOKENS, BATCH_DISCOUNT_PCT, ROW_HASH, VALID_FROM "
            "FROM CURATED.FACT_MODEL_PRICE_HISTORY WHERE IS_CURRENT = TRUE"
        )
        existing: dict[str, Scd2Row[NormalizedModelPrice]] = {}
        for row in cur.fetchall():
            model_payload = NormalizedModelPrice(
                model_id=row[0],
                price_input_usd_per_1m_tokens=float(row[1] or 0),
                price_output_usd_per_1m_tokens=float(row[2] or 0),
                price_cached_input_usd_per_1m_tokens=float(row[3]) if row[3] is not None else None,
                batch_discount_pct=float(row[4]) if row[4] is not None else None,
                tier_notes=None,
                source_url="",
                retrieved_at=as_of,
            )
            existing[row[0]] = Scd2Row(
                natural_key=row[0],
                payload=model_payload,
                row_hash=row[5],
                valid_from=row[6],
                valid_to=None,
                is_current=True,
            )

        incoming: dict[str, tuple[NormalizedModelPrice, str]] = {}
        for mp in model_prices:
            h = model_price_hash(
                mp.price_input_usd_per_1m_tokens,
                mp.price_output_usd_per_1m_tokens,
                mp.price_cached_input_usd_per_1m_tokens,
                mp.batch_discount_pct,
            )
            incoming[mp.model_id] = (mp, h)

        changeset = merge_scd2(existing_current=existing, incoming=incoming, as_of=as_of)
        for key in changeset.close_keys:
            cur.execute(
                "UPDATE CURATED.FACT_MODEL_PRICE_HISTORY SET IS_CURRENT=FALSE, VALID_TO=%s "
                "WHERE MODEL_ID=%s AND IS_CURRENT=TRUE",
                (as_of, key),
            )
        for row in changeset.insert_rows:
            mp_ins = row.payload
            cur.execute(
                "INSERT INTO CURATED.FACT_MODEL_PRICE_HISTORY ("
                "MODEL_ID, PRICE_INPUT_USD_PER_1M_TOKENS, PRICE_OUTPUT_USD_PER_1M_TOKENS, "
                "PRICE_CACHED_INPUT_USD_PER_1M_TOKENS, BATCH_DISCOUNT_PCT, TIER_NOTES, "
                "VALID_FROM, VALID_TO, IS_CURRENT, SOURCE_URL, RETRIEVED_AT, ROW_HASH"
                ") VALUES (%s,%s,%s,%s,%s,%s,%s,NULL,TRUE,%s,%s,%s)",
                (
                    mp_ins.model_id,
                    mp_ins.price_input_usd_per_1m_tokens,
                    mp_ins.price_output_usd_per_1m_tokens,
                    mp_ins.price_cached_input_usd_per_1m_tokens,
                    mp_ins.batch_discount_pct,
                    mp_ins.tier_notes,
                    row.valid_from,
                    mp_ins.source_url,
                    mp_ins.retrieved_at,
                    row.row_hash,
                ),
            )
        counts["model_price_closes"] = len(changeset.close_keys)
        counts["model_price_inserts"] = len(changeset.insert_rows)

        # Benchmarks (latest wins upsert)
        for b in benchmarks:
            cur.execute(
                """
                MERGE INTO CURATED.FACT_BENCHMARK_SCORE t
                USING (
                  SELECT %s AS MODEL_ID, %s AS BENCHMARK_NAME, %s AS SCORE, %s AS SCORE_TYPE,
                         %s AS EVAL_DATE, %s AS SOURCE_URL, %s AS RETRIEVED_AT
                ) s
                ON t.MODEL_ID = s.MODEL_ID AND t.BENCHMARK_NAME = s.BENCHMARK_NAME
                WHEN MATCHED THEN UPDATE SET
                  SCORE=s.SCORE, SCORE_TYPE=s.SCORE_TYPE, EVAL_DATE=s.EVAL_DATE,
                  SOURCE_URL=s.SOURCE_URL,
                  RETRIEVED_AT=s.RETRIEVED_AT,
                  UPDATED_AT=CURRENT_TIMESTAMP()
                WHEN NOT MATCHED THEN INSERT (
                  MODEL_ID, BENCHMARK_NAME, SCORE, SCORE_TYPE, EVAL_DATE, SOURCE_URL, RETRIEVED_AT
                ) VALUES (
                  s.MODEL_ID, s.BENCHMARK_NAME, s.SCORE, s.SCORE_TYPE, s.EVAL_DATE,
                  s.SOURCE_URL, s.RETRIEVED_AT
                )
                """,
                (
                    b.model_id,
                    b.benchmark_name,
                    b.score,
                    b.score_type.value,
                    b.eval_date,
                    str(b.source_url),
                    b.retrieved_at or as_of,
                ),
            )
        counts["benchmarks"] = len(benchmarks)

        # GPU dims + SCD2
        for g in gpu_instances:
            cur.execute(
                """
                MERGE INTO CURATED.DIM_GPU_INSTANCE t
                USING (
                  SELECT %s AS INSTANCE_ID, %s AS CLOUD, %s AS INSTANCE_NAME, %s AS GPU_MODEL,
                         %s AS GPU_COUNT, %s AS VRAM_GB, %s AS REGION_SCOPE
                ) s ON t.INSTANCE_ID = s.INSTANCE_ID
                WHEN MATCHED THEN UPDATE SET
                  CLOUD=s.CLOUD, INSTANCE_NAME=s.INSTANCE_NAME, GPU_MODEL=s.GPU_MODEL,
                  GPU_COUNT=s.GPU_COUNT, VRAM_GB=s.VRAM_GB, REGION_SCOPE=s.REGION_SCOPE,
                  UPDATED_AT=CURRENT_TIMESTAMP()
                WHEN NOT MATCHED THEN INSERT (
                  INSTANCE_ID, CLOUD, INSTANCE_NAME, GPU_MODEL, GPU_COUNT, VRAM_GB, REGION_SCOPE
                ) VALUES (
                  s.INSTANCE_ID, s.CLOUD, s.INSTANCE_NAME, s.GPU_MODEL, s.GPU_COUNT,
                  s.VRAM_GB, s.REGION_SCOPE
                )
                """,
                (
                    g.instance_id,
                    g.cloud,
                    g.instance_name,
                    g.gpu_model,
                    g.gpu_count,
                    g.vram_gb,
                    g.region_scope,
                ),
            )
        counts["gpu_instances"] = len(gpu_instances)

        cur.execute(
            "SELECT INSTANCE_ID||'|'||REGION, PRICE_ON_DEMAND_USD_HR, PRICE_SPOT_USD_HR, "
            "PRICE_1YR_RESERVED_USD_HR, ROW_HASH, VALID_FROM "
            "FROM CURATED.FACT_GPU_PRICE_HISTORY WHERE IS_CURRENT = TRUE"
        )
        gpu_existing: dict[str, Scd2Row[NormalizedGpuPrice]] = {}
        for row in cur.fetchall():
            parts = row[0].split("|", 1)
            gpu_payload = NormalizedGpuPrice(
                instance_id=parts[0],
                region=parts[1],
                price_on_demand_usd_hr=float(row[1]) if row[1] is not None else None,
                price_spot_usd_hr=float(row[2]) if row[2] is not None else None,
                price_1yr_reserved_usd_hr=float(row[3]) if row[3] is not None else None,
                source_url="",
                retrieved_at=as_of,
            )
            gpu_existing[row[0]] = Scd2Row(
                natural_key=row[0],
                payload=gpu_payload,
                row_hash=row[4],
                valid_from=row[5],
                valid_to=None,
                is_current=True,
            )

        gpu_incoming: dict[str, tuple[NormalizedGpuPrice, str]] = {}
        for gp in gpu_prices:
            key = f"{gp.instance_id}|{gp.region}"
            h = gpu_price_hash(
                gp.price_on_demand_usd_hr, gp.price_spot_usd_hr, gp.price_1yr_reserved_usd_hr
            )
            gpu_incoming[key] = (gp, h)

        gpu_cs = merge_scd2(existing_current=gpu_existing, incoming=gpu_incoming, as_of=as_of)
        for key in gpu_cs.close_keys:
            instance_id, region = key.split("|", 1)
            cur.execute(
                "UPDATE CURATED.FACT_GPU_PRICE_HISTORY SET IS_CURRENT=FALSE, VALID_TO=%s "
                "WHERE INSTANCE_ID=%s AND REGION=%s AND IS_CURRENT=TRUE",
                (as_of, instance_id, region),
            )
        for row in gpu_cs.insert_rows:
            gp_ins = row.payload
            cur.execute(
                "INSERT INTO CURATED.FACT_GPU_PRICE_HISTORY ("
                "INSTANCE_ID, REGION, PRICE_ON_DEMAND_USD_HR, PRICE_SPOT_USD_HR, "
                "PRICE_1YR_RESERVED_USD_HR, VALID_FROM, VALID_TO, IS_CURRENT, "
                "SOURCE_URL, RETRIEVED_AT, ROW_HASH"
                ") VALUES (%s,%s,%s,%s,%s,%s,NULL,TRUE,%s,%s,%s)",
                (
                    gp_ins.instance_id,
                    gp_ins.region,
                    gp_ins.price_on_demand_usd_hr,
                    gp_ins.price_spot_usd_hr,
                    gp_ins.price_1yr_reserved_usd_hr,
                    row.valid_from,
                    gp_ins.source_url,
                    gp_ins.retrieved_at,
                    row.row_hash,
                ),
            )
        counts["gpu_price_inserts"] = len(gpu_cs.insert_rows)

        # Cortex SCD2
        cur.execute(
            "SELECT FUNCTION_NAME||'|'||MODEL_NAME, CREDITS_PER_1M_TOKENS, ROW_HASH, VALID_FROM "
            "FROM CURATED.FACT_CORTEX_PRICE_HISTORY WHERE IS_CURRENT = TRUE"
        )
        cortex_existing: dict[str, Scd2Row[CortexPriceSeed]] = {}
        for row in cur.fetchall():
            fn, mn = row[0].split("|", 1)
            cortex_payload = CortexPriceSeed(
                function_name=fn,
                model_name=mn,
                credits_per_1m_tokens=float(row[1]),
                source_url="https://docs.snowflake.com/",  # type: ignore[arg-type]
                retrieved_at=as_of,
            )
            cortex_existing[row[0]] = Scd2Row(
                natural_key=row[0],
                payload=cortex_payload,
                row_hash=row[2],
                valid_from=row[3],
                valid_to=None,
                is_current=True,
            )

        cortex_incoming: dict[str, tuple[CortexPriceSeed, str]] = {}
        for c in cortex:
            key = f"{c.function_name}|{c.model_name}"
            cortex_incoming[key] = (c, cortex_price_hash(c.credits_per_1m_tokens))

        cortex_cs = merge_scd2(
            existing_current=cortex_existing, incoming=cortex_incoming, as_of=as_of
        )
        for key in cortex_cs.close_keys:
            fn, mn = key.split("|", 1)
            cur.execute(
                "UPDATE CURATED.FACT_CORTEX_PRICE_HISTORY SET IS_CURRENT=FALSE, VALID_TO=%s "
                "WHERE FUNCTION_NAME=%s AND MODEL_NAME=%s AND IS_CURRENT=TRUE",
                (as_of, fn, mn),
            )
        for row in cortex_cs.insert_rows:
            c = row.payload
            cur.execute(
                "INSERT INTO CURATED.FACT_CORTEX_PRICE_HISTORY ("
                "FUNCTION_NAME, MODEL_NAME, CREDITS_PER_1M_TOKENS, VALID_FROM, VALID_TO, "
                "IS_CURRENT, SOURCE_URL, RETRIEVED_AT, ROW_HASH"
                ") VALUES (%s,%s,%s,%s,NULL,TRUE,%s,%s,%s)",
                (
                    c.function_name,
                    c.model_name,
                    c.credits_per_1m_tokens,
                    row.valid_from,
                    str(c.source_url),
                    c.retrieved_at or as_of,
                    row.row_hash,
                ),
            )
        counts["cortex_price_inserts"] = len(cortex_cs.insert_rows)

        # Refresh log + quality
        cur.execute(
            "INSERT INTO CURATED._META_REFRESH_LOG "
            "(REFRESH_ID, STARTED_AT, FINISHED_AT, STATUS, ROWS_UPSERTED, MESSAGE) "
            "SELECT %s, %s, CURRENT_TIMESTAMP(), %s, PARSE_JSON(%s), %s",
            (refresh_id, started_at, "RUNNING", json.dumps(counts), None),
        )

        failures = run_quality_checks(cur)
        status = "SUCCESS" if not failures else "FAILED"
        message = None if not failures else "; ".join(failures)
        cur.execute(
            "UPDATE CURATED._META_REFRESH_LOG SET STATUS=%s, FINISHED_AT=CURRENT_TIMESTAMP(), "
            "MESSAGE=%s, ROWS_UPSERTED=PARSE_JSON(%s) WHERE REFRESH_ID=%s",
            (status, message, json.dumps(counts), refresh_id),
        )
        conn.commit()
        if failures:
            raise RuntimeError(f"Quality checks failed: {message}")
        return counts
    finally:
        conn.close()


def run_quality_checks(cur: Any) -> list[str]:
    """Execute SELECT quality checks; any returned FAIL_COUNT > 0 is a failure."""
    sql = QUALITY_SQL.read_text(encoding="utf-8")
    failures: list[str] = []
    # Split on semicolons; only run SELECTs
    for chunk in sql.split(";"):
        stmt = chunk.strip()
        if not stmt or stmt.startswith("--"):
            lines = [
                ln for ln in stmt.splitlines() if ln.strip() and not ln.strip().startswith("--")
            ]
            stmt = "\n".join(lines).strip()
        if not stmt.upper().startswith("SELECT"):
            continue
        try:
            cur.execute(stmt)
            rows = cur.fetchall()
            for row in rows:
                check_name = row[0]
                fail_count = row[1]
                if fail_count and int(fail_count) > 0:
                    failures.append(f"{check_name}={fail_count}")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"QUALITY_EXEC_ERROR:{exc}")
    return failures
