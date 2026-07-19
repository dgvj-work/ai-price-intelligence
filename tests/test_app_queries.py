"""SQL lint / dry-parse tests for native app queries."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STREAMLIT = ROOT / "native_app" / "src" / "streamlit"
sys.path.insert(0, str(STREAMLIT))

import queries  # noqa: E402

FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|DROP|ALTER|COPY|PUT|GET)\b",
    re.IGNORECASE,
)


@pytest.mark.parametrize("days", [30, 60, 90])
def test_spend_sql_is_select_only(days: int) -> None:
    sql = queries.sql_cortex_spend(days)
    assert sql.strip().upper().startswith("SELECT")
    assert FORBIDDEN.search(sql) is None
    assert "V_CORTEX_USAGE" in sql
    assert "USAGE_TIME" in sql
    assert f"-{days}" in sql or f"-{int(days)}" in sql


def test_no_query_history_or_deprecated_cortex_view() -> None:
    text = Path(STREAMLIT / "queries.py").read_text(encoding="utf-8")
    assert "QUERY_HISTORY" not in text
    assert "CORTEX_FUNCTIONS_USAGE_HISTORY" not in text
    assert "REFERENCE(" in text


def test_ensure_views_call() -> None:
    assert "ENSURE_ACCOUNT_USAGE_VIEWS" in queries.SQL_ENSURE_VIEWS


def test_all_builders_parse() -> None:
    for fn in (
        queries.sql_cortex_top,
        queries.sql_metering_fallback,
        queries.sql_usage_by_model,
    ):
        sql = fn(90)
        assert "SELECT" in sql.upper()
        assert FORBIDDEN.search(sql) is None


def test_setup_script_uses_current_cortex_views() -> None:
    setup = (ROOT / "native_app" / "app" / "setup_script.sql").read_text(encoding="utf-8")
    assert "CORTEX_AI_FUNCTIONS_USAGE_HISTORY" in setup
    assert "ENSURE_ACCOUNT_USAGE_VIEWS" in setup
    assert "QUERY_HISTORY" not in setup
    # Deprecated view must not be the primary source
    assert "FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_FUNCTIONS_USAGE_HISTORY" not in setup
    # Tokens must use LATERAL FLATTEN join (scalar FLATTEN subquery fails in VIEWs).
    assert "LEFT JOIN LATERAL FLATTEN(INPUT => m.METRICS)" in setup
    assert "FROM TABLE(FLATTEN(INPUT => m.METRICS))" not in setup
    assert "SELECT COUNT(*) INTO :probe_cnt FROM APP_SCHEMA.V_CORTEX_USAGE" in setup


def test_manifest_has_dataset_references() -> None:
    manifest = (ROOT / "native_app" / "app" / "manifest.yml").read_text(encoding="utf-8")
    assert "price_intel_cortex_current" in manifest
    assert "price_intel_model_current" in manifest
    assert "price_intel_price_changes" in manifest
    assert "register_callback" in manifest
