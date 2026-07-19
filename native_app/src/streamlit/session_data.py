"""Shared data helpers for Streamlit screens (not under pages/ — avoids multipage clash)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import pandas as pd
import streamlit as st

import demo_data
import queries

SNAPSHOT_PATH = Path(__file__).resolve().parent / "data" / "price_snapshot.csv"

APP_VERSION = "1.0.1"  # keep in sync with manifest.yml version.label

# Internal procedure return values → never shown raw in the UI.
_LIVE_SOURCES = {
    "CORTEX_AI_FUNCTIONS_USAGE_HISTORY": "Cortex AI Functions usage history",
    "CORTEX_AISQL_USAGE_HISTORY": "Cortex AI SQL usage history",
}
_PENDING = frozenset({"PENDING_PRIVILEGES", "EMPTY_STUB", "OK"})

# live = real ACCOUNT_USAGE rows
# preview = privileges missing — sample data + connect CTA
# sample = privileges OK but no rows in window — sample data, no connect CTA
DataMode = Literal["live", "preview", "sample"]


def classify_source(source: str | None) -> Literal["live", "needs_privilege", "unknown"]:
    if not source:
        return "needs_privilege"
    if source in _LIVE_SOURCES:
        return "live"
    if source in _PENDING or source == "ENSURE_FAILED" or source.startswith("ENSURE_FAILED"):
        return "needs_privilege"
    # Unexpected token — treat as not live; never echo it.
    return "unknown"


def needs_setup(source: str | None) -> bool:
    return classify_source(source) != "live"


def humanize_source(source: str | None) -> str | None:
    if not source:
        return None
    return _LIVE_SOURCES.get(source)


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
        if not rows:
            return "PENDING_PRIVILEGES"
        raw = str(rows[0][0])
        # Never persist exception payloads in session state.
        if raw.startswith("ENSURE_FAILED") or "Error" in raw:
            return "ENSURE_FAILED"
        if raw in _LIVE_SOURCES or raw in _PENDING:
            return raw
        if raw in ("EMPTY_STUB",):
            return "PENDING_PRIVILEGES"
        return "PENDING_PRIVILEGES"
    except Exception:  # noqa: BLE001
        return "ENSURE_FAILED"


def init_usage_session(*, force: bool = False) -> None:
    """Auto-refresh usage views once per browser session (and on force)."""
    if force or "usage_source" not in st.session_state:
        st.session_state["usage_source"] = ensure_usage_views()


@st.cache_data(ttl=900, show_spinner="Loading Cortex usage…")
def _load_cortex_spend_live(days: int) -> pd.DataFrame:
    session = _session()
    if session is None:
        return pd.DataFrame()
    try:
        return session.sql(queries.sql_cortex_spend(days)).to_pandas()
    except Exception:  # noqa: BLE001
        return pd.DataFrame()


@st.cache_data(ttl=900, show_spinner="Loading top functions…")
def _load_cortex_top_live(days: int) -> pd.DataFrame:
    session = _session()
    if session is None:
        return pd.DataFrame()
    try:
        return session.sql(queries.sql_cortex_top(days)).to_pandas()
    except Exception:  # noqa: BLE001
        return pd.DataFrame()


@st.cache_data(ttl=900, show_spinner="Loading metering…")
def _load_metering_live(days: int) -> pd.DataFrame:
    session = _session()
    if session is None:
        return pd.DataFrame()
    try:
        return session.sql(queries.sql_metering_fallback(days)).to_pandas()
    except Exception:  # noqa: BLE001
        return pd.DataFrame()


@st.cache_data(ttl=900)
def _load_usage_by_model_live(days: int) -> pd.DataFrame:
    session = _session()
    if session is None:
        return pd.DataFrame()
    try:
        return session.sql(queries.sql_usage_by_model(days)).to_pandas()
    except Exception:  # noqa: BLE001
        return pd.DataFrame()


def load_cortex_spend(days: int) -> tuple[pd.DataFrame, DataMode]:
    if needs_setup(st.session_state.get("usage_source")):
        return demo_data.demo_cortex_spend(days), "preview"
    df = _load_cortex_spend_live(days)
    if not df.empty:
        return df, "live"
    return demo_data.demo_cortex_spend(days), "sample"


def load_cortex_top(days: int) -> tuple[pd.DataFrame, DataMode]:
    if needs_setup(st.session_state.get("usage_source")):
        return demo_data.demo_cortex_top(), "preview"
    df = _load_cortex_top_live(days)
    if not df.empty:
        return df, "live"
    return demo_data.demo_cortex_top(), "sample"


def load_metering(days: int) -> tuple[pd.DataFrame, DataMode]:
    if needs_setup(st.session_state.get("usage_source")):
        return pd.DataFrame(), "preview"
    df = _load_metering_live(days)
    if not df.empty:
        return df, "live"
    return pd.DataFrame(), "sample"


def load_usage_by_model(days: int) -> tuple[pd.DataFrame, DataMode]:
    if needs_setup(st.session_state.get("usage_source")):
        return demo_data.demo_usage_by_model(), "preview"
    df = _load_usage_by_model_live(days)
    if not df.empty:
        return df, "live"
    return demo_data.demo_usage_by_model(), "sample"


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
    except Exception:  # noqa: BLE001
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


def empty_state(message: str) -> None:
    st.info(message)


def mode_banner(mode: DataMode) -> None:
    if mode == "preview":
        st.info(
            "**Preview mode** — sample Cortex spend so you can evaluate the product "
            "immediately. Connect your account (section below) to replace this with live "
            "ACCOUNT_USAGE data. Sample rows are not your billed usage."
        )
    elif mode == "sample":
        st.info(
            "**Connected — no Cortex rows in this window yet.** Showing sample charts so "
            "the product stays usable. Run Cortex / AI functions, wait up to ~45 minutes "
            "for ACCOUNT_USAGE lag, then reopen the app (views refresh automatically)."
        )
    else:
        label = humanize_source(st.session_state.get("usage_source"))
        suffix = f" ({label})" if label else ""
        st.success(f"**Live mode** — reading your account’s Cortex / AI metering{suffix}.")
