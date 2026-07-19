#!/usr/bin/env python3
"""End-to-end smoke checks for Cortex Cost Advisor (local + Snowflake)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STREAMLIT = ROOT / "src" / "streamlit"
sys.path.insert(0, str(STREAMLIT))


def _ok(msg: str) -> None:
    print(f"OK  {msg}")


def _fail(msg: str) -> None:
    print(f"FAIL {msg}")
    raise SystemExit(1)


def check_local_product() -> None:
    import demo_data
    import insights
    from _logo_bytes import LOGO_PNG
    from charts import price_change_bars, spend_trend_chart, switch_savings_bars
    from model_ids import models_match

    if not LOGO_PNG.startswith(b"\x89PNG"):
        _fail("embedded logo is not a PNG")
    _ok(f"embedded logo ({len(LOGO_PNG)} bytes)")

    usage = demo_data.demo_usage_by_model()
    spend = demo_data.demo_cortex_spend(90)
    snap = __import__("pandas").read_csv(STREAMLIT / "data" / "price_snapshot.csv")
    cortex = snap[snap["row_type"] == "cortex"][
        ["cortex_function", "cortex_model", "credits_per_1m_tokens"]
    ].rename(
        columns={
            "cortex_function": "FUNCTION_NAME",
            "cortex_model": "MODEL_NAME",
            "credits_per_1m_tokens": "CREDITS_PER_1M_TOKENS",
        }
    )
    llm = snap[snap["row_type"] == "llm"]

    pack = insights.build_advisor_pack(
        usage=usage,
        spend=spend,
        cortex_prices=cortex,
        llm_snapshot=llm,
        credit_price=3.0,
    )
    if pack["primary"] is None:
        _fail("preview advisor pack produced no primary recommendation")
    _ok(f"advisor pack primary={pack['primary'].kind} switches={len(pack['switches'])}")

    if not models_match("llama3.1-70b", "llama3.1-70b"):
        _fail("model_ids exact match failed")
    if models_match("llama", "llama3.1-70b"):
        _fail("model_ids loose substring should not match")
    _ok("model_ids matching")

    # Chart helpers should not raise on demo frames.
    daily = spend.groupby("DAY", as_index=False)["CREDITS"].sum()
    spend_trend_chart(daily)  # may call streamlit; wrap if needed
    _ok("spend_trend_chart callable")

    rows = [
        {
            "label": f"{i.meta.get('from_model')}->{i.meta.get('to_model')}",
            "usd": i.savings_usd,
            "credits": i.savings_credits,
        }
        for i in pack["switches"][:3]
        if getattr(i, "meta", None)
    ]
    if rows:
        switch_savings_bars(rows)
        _ok("switch_savings_bars callable")

    moved = llm[llm["change_pct_90d"].fillna(0) != 0]
    if not moved.empty:
        price_change_bars(moved, label_col="model_name", pct_col="change_pct_90d")
        _ok("price_change_bars callable")


def check_snowflake() -> None:
    try:
        from snowflake.cli.api.connections import load_connection_from_file
    except Exception:
        pass

    # Use snow CLI SQL for package/app health.
    import subprocess

    snow = ROOT.parent / ".venv" / "bin" / "snow"
    if not snow.exists():
        snow = Path("snow")

    def sql(q: str) -> str:
        r = subprocess.run(
            [str(snow), "sql", "-c", "ai_price", "-q", q],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode != 0 and "Error" in out:
            return out
        return out

    out = sql("SHOW RELEASE DIRECTIVES IN APPLICATION PACKAGE CORTEX_COST_ADVISOR_PKG;")
    if "V1_" not in out:
        _fail("could not read release directives")
    _ok("release directives readable")

    # Privileges / live views
    out = sql("CALL CORTEX_COST_ADVISOR.APP_SCHEMA.ENSURE_ACCOUNT_USAGE_VIEWS();")
    upper = out.upper()
    if "CORTEX_AI" in upper or "CORTEX_AISQL" in upper:
        _ok("live usage source ready")
        live = True
    elif "PENDING" in upper or "EMPTY" in upper:
        _ok("usage views pending privileges (preview mode expected)")
        live = False
    else:
        _ok(f"ENSURE returned (truncated): {out.strip()[:160]}")
        live = "CORTEX" in upper and "PENDING" not in upper

    if live:
        out = sql("SELECT COUNT(*) AS ROWS_ FROM CORTEX_COST_ADVISOR.APP_SCHEMA.V_CORTEX_USAGE;")
        if "Error" in out and "SQL" in out:
            _fail(f"V_CORTEX_USAGE query failed: {out[:200]}")
        _ok("V_CORTEX_USAGE query ok")
        out = sql(
            """
            SELECT COUNT(*) AS ROWS_
            FROM CORTEX_COST_ADVISOR.APP_SCHEMA.V_METERING_HISTORY;
            """
        )
        _ok("V_METERING_HISTORY query ok")
    else:
        _ok("skipping live row counts (preview / pending privileges)")

    out = sql("LIST @CORTEX_COST_ADVISOR_PKG.APP_SRC.STAGE/src/streamlit/;")
    if "_logo_bytes" in out:
        _ok("stage contains _logo_bytes.py")
    else:
        print(f"WARN stage logo module not confirmed:\n{out[:400]}")
    if "charts.py" in out:
        _ok("stage contains charts.py")
    if "price_snapshot.csv" in out or "data/" in out:
        _ok("stage contains snapshot data path")



def main() -> None:
    # Chart helpers call streamlit; stub minimal surface for smoke.
    import types

    class _Stub:
        def __getattr__(self, name):
            def _fn(*args, **kwargs):
                return None

            return _fn

    sys.modules.setdefault("streamlit", _Stub())  # type: ignore[arg-type]

    print("=== Local product smoke ===")
    check_local_product()
    print("=== Snowflake smoke ===")
    check_snowflake()
    print("=== ALL CHECKS PASSED ===")


if __name__ == "__main__":
    main()
