"""Shared data helpers for Streamlit screens (not under pages/ — avoids multipage clash)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

import queries

SNAPSHOT_PATH = Path(__file__).resolve().parent / "data" / "price_snapshot.csv"

# Consumer-facing labels for ENSURE_ACCOUNT_USAGE_VIEWS() return values.
# Internal sentinel PENDING_PRIVILEGES (and legacy EMPTY_STUB) are never shown raw.
_SOURCE_LABELS = {
    "CORTEX_AI_FUNCTIONS_USAGE_HISTORY": "Cortex AI Functions usage history",
    "CORTEX_AISQL_USAGE_HISTORY": "Cortex AI SQL usage history",
    "PENDING_PRIVILEGES": None,
    "EMPTY_STUB": None,
}


def humanize_source(source: str | None) -> str | None:
    if not source:
        return None
    if source.startswith("ENSURE_FAILED"):
        return "Waiting for privileges or ACCOUNT_USAGE access"
    if source in _SOURCE_LABELS:
        return _SOURCE_LABELS[source]
    return source


def needs_setup(source: str | None) -> bool:
    """True when privileges are missing or usage views could not be created."""
    if source is None:
        return True
    if source in ("PENDING_PRIVILEGES", "EMPTY_STUB"):
        return True
    if source.startswith("ENSURE_FAILED"):
        return True
    return False


def _session() -> Any:
    try:
        from snowflake.snowpark.context import get_active_session

        return get_active_session()
    except Exception:  # noqa: BLE001
        return None


def ensure_usage_views() -> str | None:
    """Recreate ACCOUNT_USAGE views after consumer grants imported privileges."""
    session = _session()
    if session is None:
        return None
    try:
        rows = session.sql(queries.SQL_ENSURE_VIEWS).collect()
        if rows:
            return str(rows[0][0])
        return "OK"
    except Exception as exc:  # noqa: BLE001
        return f"ENSURE_FAILED:{exc}"


@st.cache_data(ttl=3600, show_spinner="Loading Cortex usage…")
def load_cortex_spend(days: int) -> pd.DataFrame:
    session = _session()
    if session is None:
        return pd.DataFrame()
    try:
        return session.sql(queries.sql_cortex_spend(days)).to_pandas()
    except Exception as exc:  # noqa: BLE001
        st.caption(f"Cortex usage query unavailable: {exc}")
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner="Loading top functions…")
def load_cortex_top(days: int) -> pd.DataFrame:
    session = _session()
    if session is None:
        return pd.DataFrame()
    try:
        return session.sql(queries.sql_cortex_top(days)).to_pandas()
    except Exception as exc:  # noqa: BLE001
        st.caption(f"Top functions query unavailable: {exc}")
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner="Loading metering…")
def load_metering(days: int) -> pd.DataFrame:
    session = _session()
    if session is None:
        return pd.DataFrame()
    try:
        return session.sql(queries.sql_metering_fallback(days)).to_pandas()
    except Exception as exc:  # noqa: BLE001
        st.caption(f"Metering query unavailable: {exc}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_snapshot() -> pd.DataFrame:
    if not SNAPSHOT_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(SNAPSHOT_PATH)


@st.cache_data(ttl=3600, show_spinner="Loading bound dataset…")
def load_ref_model_current() -> pd.DataFrame:
    session = _session()
    if session is None:
        return pd.DataFrame()
    try:
        return session.sql(queries.SQL_REF_MODEL_CURRENT).to_pandas()
    except Exception:  # noqa: BLE001 — reference unbound
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_ref_cortex_current() -> pd.DataFrame:
    session = _session()
    if session is None:
        return pd.DataFrame()
    try:
        return session.sql(queries.SQL_REF_CORTEX_CURRENT).to_pandas()
    except Exception:  # noqa: BLE001
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_ref_price_changes() -> pd.DataFrame:
    session = _session()
    if session is None:
        return pd.DataFrame()
    try:
        return session.sql(queries.SQL_REF_PRICE_CHANGES).to_pandas()
    except Exception:  # noqa: BLE001
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_usage_by_model(days: int) -> pd.DataFrame:
    session = _session()
    if session is None:
        return pd.DataFrame()
    try:
        return session.sql(queries.sql_usage_by_model(days)).to_pandas()
    except Exception as exc:  # noqa: BLE001
        st.caption(f"Usage-by-model query unavailable: {exc}")
        return pd.DataFrame()


def empty_state(message: str) -> None:
    st.info(message)
