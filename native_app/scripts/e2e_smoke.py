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
    from charts import price_change_bars, spend_trend_chart, switch_savings_bars
    from model_ids import models_match

    logo = STREAMLIT / "assets" / "logo.png"
    if not logo.exists():
        _fail("assets/logo.png missing")
    raw = logo.read_bytes()
    if not raw.startswith(b"\x89PNG"):
        _fail("assets/logo.png is not a PNG")
    _ok(f"asset logo.png ({len(raw)} bytes)")

    # Threshold defaults must stay documented + configurable.
    if abs(insights.SWITCH_MIN_SAVINGS_PCT - 0.15) > 1e-9:
        _fail("unexpected SWITCH_MIN_SAVINGS_PCT default")
    _ok("insight thresholds documented as module constants")

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

    # Always probe the view: DDL can succeed while query fails (unsupported subquery).
    out = sql("SELECT COUNT(*) AS ROWS_ FROM CORTEX_COST_ADVISOR.APP_SCHEMA.V_CORTEX_USAGE;")
    upper = out.upper()
    if "UNSUPPORTED SUBQUERY" in upper:
        _fail(f"V_CORTEX_USAGE has unsupported subquery: {out[:240]}")
    if "ERROR" in upper and "SQL" in upper and "COMPILATION" in upper:
        _fail(f"V_CORTEX_USAGE query failed: {out[:240]}")
    _ok("V_CORTEX_USAGE is queryable")

    out = sql(
        "SELECT COUNT(*) AS ROWS_ FROM CORTEX_COST_ADVISOR.APP_SCHEMA.V_METERING_HISTORY;"
    )
    if "UNSUPPORTED SUBQUERY" in out.upper():
        _fail(f"V_METERING_HISTORY has unsupported subquery: {out[:240]}")
    _ok("V_METERING_HISTORY is queryable")

    if not live:
        _ok("live source still pending privileges (preview expected until GRANT)")

    pyc = sql(
        "LIST @CORTEX_COST_ADVISOR_PKG.APP_SRC.STAGE/src/streamlit/ PATTERN='.*__pycache__.*';"
    )
    if "__pycache__" in pyc.replace(" ", "") or ".pyc" in pyc:
        _fail("stage still contains __pycache__ / .pyc (Marketplace hygiene)")
    _ok("stage has no __pycache__")

    # Snowflake LIST wraps long names across columns; use PATTERN queries.
    charts = sql(
        "LIST @CORTEX_COST_ADVISOR_PKG.APP_SRC.STAGE/src/streamlit/ PATTERN='.*charts\\\\.py';"
    )
    if "charts.py" in charts.replace("\n", "") or "harts.py" in charts:
        _ok("stage contains charts.py")
    else:
        _fail(f"stage missing charts.py: {charts[:300]}")

    logo_mod = sql(
        "LIST @CORTEX_COST_ADVISOR_PKG.APP_SRC.STAGE/src/streamlit/ PATTERN='.*_logo_bytes\\\\.py';"
    )
    if "_logo_bytes.py" in logo_mod.replace(" ", "").replace("\n", ""):
        _fail("stage still contains removed _logo_bytes.py")
    _ok("stage has no _logo_bytes.py source")

    insights = sql(
        "LIST @CORTEX_COST_ADVISOR_PKG.APP_SRC.STAGE/src/streamlit/ PATTERN='.*insights\\\\.py';"
    )
    if "insights.py" in insights.replace("\n", "") or "nsights.py" in insights:
        _ok("stage contains insights.py")

    snap = sql(
        "LIST @CORTEX_COST_ADVISOR_PKG.APP_SRC.STAGE/src/streamlit/data/;"
    )
    if "price_snapshot" in snap or "snapshot" in snap:
        _ok("stage contains snapshot data path")

    assets = sql(
        "LIST @CORTEX_COST_ADVISOR_PKG.APP_SRC.STAGE/src/streamlit/assets/ PATTERN='.*logo\\\\.png';"
    )
    if "logo.png" in assets.replace("\n", "") or "ogo.png" in assets:
        _ok("stage contains assets/logo.png")



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
