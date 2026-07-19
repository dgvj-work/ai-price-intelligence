"""Shared data helpers for Streamlit screens (not under pages/ — avoids multipage clash)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import pandas as pd
import streamlit as st

import demo_data
import queries

SNAPSHOT_PATH = Path(__file__).resolve().parent / "data" / "price_snapshot.csv"

APP_VERSION = "1.1.1"  # keep in sync with manifest.yml version.label

# Internal procedure return values → never shown raw in the UI.
_LIVE_SOURCES = {
    "CORTEX_AI_FUNCTIONS_USAGE_HISTORY": "Cortex AI Functions usage history",
    "CORTEX_AISQL_USAGE_HISTORY": "Cortex AI SQL usage history",
}
_PENDING = frozenset({"PENDING_PRIVILEGES", "EMPTY_STUB", "OK"})
_BLOCKED_UI_TOKENS = ("EMPTY_STUB", "PENDING_PRIVILEGES", "ENSURE_FAILED")

# live = real ACCOUNT_USAGE rows
# preview = privileges missing — sample data + connect CTA
# sample = privileges OK but no rows in window — sample data, no connect CTA
DataMode = Literal["live", "preview", "sample"]


def sanitize_source_token(source: str | None) -> str | None:
    """Map procedure return values to safe session tokens. Never keep EMPTY_STUB."""
    if not source:
        return None
    raw = str(source).strip()
    if raw in _LIVE_SOURCES:
        return raw
    if raw == "EMPTY_STUB" or "EMPTY_STUB" in raw.upper():
        return "PENDING_PRIVILEGES"
    if raw.startswith("ENSURE_FAILED") or raw == "ENSURE_FAILED":
        return "ENSURE_FAILED"
    if raw in _PENDING:
        return "PENDING_PRIVILEGES" if raw == "EMPTY_STUB" else raw
    # Unknown / leaky payloads → pending, never echo to UI
    return "PENDING_PRIVILEGES"


def classify_source(source: str | None) -> Literal["live", "needs_privilege", "unknown"]:
    token = sanitize_source_token(source)
    if not token:
        return "needs_privilege"
    if token in _LIVE_SOURCES:
        return "live"
    if token in _PENDING or token == "ENSURE_FAILED":
        return "needs_privilege"
    return "unknown"


def needs_setup(source: str | None) -> bool:
    return classify_source(source) != "live"


def humanize_source(source: str | None) -> str | None:
    """Consumer-facing label only — never returns EMPTY_STUB or raw tokens."""
    token = sanitize_source_token(source)
    if not token:
        return None
    if token in _LIVE_SOURCES:
        return _LIVE_SOURCES[token]
    for blocked in _BLOCKED_UI_TOKENS:
        if blocked in str(source or "").upper():
            return None
    return None


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
        return sanitize_source_token(str(rows[0][0]))
    except Exception:  # noqa: BLE001
        return "ENSURE_FAILED"


def init_usage_session(*, force: bool = False) -> None:
    """Auto-refresh usage views once per browser session (and on force)."""
    if force or "usage_source" not in st.session_state:
        st.session_state["usage_source"] = ensure_usage_views()
    # Belt-and-suspenders: scrub any leaked internal tokens already in session.
    st.session_state["usage_source"] = sanitize_source_token(
        st.session_state.get("usage_source")
    )


def load_persisted_credit_price(default: float = 3.0) -> float:
    session = _session()
    if session is None:
        return default
    try:
        rows = session.sql(queries.SQL_GET_CREDIT_PRICE).collect()
        if rows and rows[0][0] is not None:
            return float(rows[0][0])
    except Exception:  # noqa: BLE001
        pass
    return default


def persist_credit_price(price: float) -> None:
    session = _session()
    if session is None:
        return
    try:
        session.sql(queries.sql_set_credit_price(price)).collect()
    except Exception:  # noqa: BLE001
        pass


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
        st.caption(
            "Showing **sample recommendations** so you can evaluate the product before "
            "connecting ACCOUNT_USAGE. Connect when an admin has granted privileges."
        )
    elif mode == "sample":
        st.caption(
            "Privileges connected, but no Cortex rows in this window yet — sample "
            "recommendations shown. ACCOUNT_USAGE can lag ~45 minutes after new AI calls."
        )
    else:
        label = humanize_source(st.session_state.get("usage_source"))
        st.caption(f"Live Cortex metering{f' · {label}' if label else ''}.")
