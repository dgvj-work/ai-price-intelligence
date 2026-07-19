"""Shared data helpers for Streamlit screens (not under pages/ — avoids multipage clash)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

import queries

SNAPSHOT_PATH = Path(__file__).resolve().parent / "data" / "price_snapshot.csv"


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
