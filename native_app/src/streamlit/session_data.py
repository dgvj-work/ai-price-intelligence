"""Shared data helpers for Streamlit screens (not under pages/ - avoids multipage clash)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import pandas as pd
import streamlit as st

import demo_data
import queries

SNAPSHOT_PATH = Path(__file__).resolve().parent / "data" / "price_snapshot.csv"

APP_VERSION = "1.1.6"  # keep in sync with manifest.yml version.label

# Internal procedure return values -> never shown raw in the UI.
_LIVE_SOURCES = {
    "CORTEX_AI_FUNCTIONS_USAGE_HISTORY": "Cortex AI Functions usage history",
    "CORTEX_AISQL_USAGE_HISTORY": "Cortex AI SQL usage history",
}
_PENDING = frozenset({"PENDING_PRIVILEGES", "EMPTY_STUB", "OK"})
_BLOCKED_UI_TOKENS = ("EMPTY_STUB", "PENDING_PRIVILEGES", "ENSURE_FAILED")

# live = real ACCOUNT_USAGE rows
# preview = privileges missing - sample data + connect CTA
# sample = privileges OK but no rows in window - sample data, no connect CTA
# error = live query failed - sample shown with warning
DataMode = Literal["live", "preview", "sample", "error"]


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
    """Consumer-facing label only - never returns EMPTY_STUB or raw tokens."""
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


def _set_load_error(key: str, message: str | None) -> None:
    errors = st.session_state.setdefault("data_load_errors", {})
    if message:
        errors[key] = message[:240]
    else:
        errors.pop(key, None)


def data_load_errors() -> dict[str, str]:
    return dict(st.session_state.get("data_load_errors") or {})


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
    """Save $/credit using bound parameters (Marketplace-review friendly)."""
    session = _session()
    if session is None:
        return
    p = queries.clamp_credit_price(price)
    try:
        session.sql(
            queries.SQL_SET_CREDIT_PRICE,
            params=["credit_price_usd", f"{p:.4f}"],
        ).collect()
    except Exception:  # noqa: BLE001
        # Fallback for connectors that reject ? binds in MERGE USING.
        try:
            session.sql(
                f"""
                MERGE INTO APP_SCHEMA.USER_SETTINGS t
                USING (SELECT 'credit_price_usd' AS SETTING_KEY) s
                ON t.SETTING_KEY = s.SETTING_KEY
                WHEN MATCHED THEN UPDATE SET
                  SETTING_VALUE = TO_VARCHAR({p:.4f}),
                  UPDATED_AT = CURRENT_TIMESTAMP()
                WHEN NOT MATCHED THEN INSERT (SETTING_KEY, SETTING_VALUE, UPDATED_AT)
                  VALUES ('credit_price_usd', TO_VARCHAR({p:.4f}), CURRENT_TIMESTAMP())
                """
            ).collect()
        except Exception:  # noqa: BLE001
            pass


@st.cache_data(ttl=900, show_spinner="Loading Cortex usage...")
def _load_cortex_spend_live(days: int) -> tuple[pd.DataFrame, str | None]:
    session = _session()
    if session is None:
        return pd.DataFrame(), "no_session"
    try:
        return session.sql(queries.sql_cortex_spend(days)).to_pandas(), None
    except Exception as exc:  # noqa: BLE001
        return pd.DataFrame(), f"{type(exc).__name__}"


@st.cache_data(ttl=900, show_spinner="Loading top functions...")
def _load_cortex_top_live(days: int) -> tuple[pd.DataFrame, str | None]:
    session = _session()
    if session is None:
        return pd.DataFrame(), "no_session"
    try:
        return session.sql(queries.sql_cortex_top(days)).to_pandas(), None
    except Exception as exc:  # noqa: BLE001
        return pd.DataFrame(), f"{type(exc).__name__}"


@st.cache_data(ttl=900, show_spinner="Loading metering...")
def _load_metering_live(days: int) -> tuple[pd.DataFrame, str | None]:
    session = _session()
    if session is None:
        return pd.DataFrame(), "no_session"
    try:
        return session.sql(queries.sql_metering_fallback(days)).to_pandas(), None
    except Exception as exc:  # noqa: BLE001
        return pd.DataFrame(), f"{type(exc).__name__}"


@st.cache_data(ttl=900)
def _load_usage_by_model_live(days: int) -> tuple[pd.DataFrame, str | None]:
    session = _session()
    if session is None:
        return pd.DataFrame(), "no_session"
    try:
        return session.sql(queries.sql_usage_by_model(days)).to_pandas(), None
    except Exception as exc:  # noqa: BLE001
        return pd.DataFrame(), f"{type(exc).__name__}"


def load_cortex_spend(days: int) -> tuple[pd.DataFrame, DataMode]:
    if needs_setup(st.session_state.get("usage_source")):
        _set_load_error("cortex_spend", None)
        return demo_data.demo_cortex_spend(days), "preview"
    df, err = _load_cortex_spend_live(days)
    if err:
        _set_load_error("cortex_spend", err)
        return demo_data.demo_cortex_spend(days), "error"
    _set_load_error("cortex_spend", None)
    if not df.empty:
        return df, "live"
    return demo_data.demo_cortex_spend(days), "sample"


def load_cortex_top(days: int) -> tuple[pd.DataFrame, DataMode]:
    if needs_setup(st.session_state.get("usage_source")):
        _set_load_error("cortex_top", None)
        return demo_data.demo_cortex_top(), "preview"
    df, err = _load_cortex_top_live(days)
    if err:
        _set_load_error("cortex_top", err)
        return demo_data.demo_cortex_top(), "error"
    _set_load_error("cortex_top", None)
    if not df.empty:
        return df, "live"
    return demo_data.demo_cortex_top(), "sample"


def load_metering(days: int) -> tuple[pd.DataFrame, DataMode]:
    if needs_setup(st.session_state.get("usage_source")):
        _set_load_error("metering", None)
        return pd.DataFrame(), "preview"
    df, err = _load_metering_live(days)
    if err:
        _set_load_error("metering", err)
        return pd.DataFrame(), "error"
    _set_load_error("metering", None)
    if not df.empty:
        return df, "live"
    return pd.DataFrame(), "sample"


def load_usage_by_model(days: int) -> tuple[pd.DataFrame, DataMode]:
    if needs_setup(st.session_state.get("usage_source")):
        _set_load_error("usage_by_model", None)
        return demo_data.demo_usage_by_model(), "preview"
    df, err = _load_usage_by_model_live(days)
    if err:
        _set_load_error("usage_by_model", err)
        return demo_data.demo_usage_by_model(), "error"
    _set_load_error("usage_by_model", None)
    if not df.empty:
        return df, "live"
    return demo_data.demo_usage_by_model(), "sample"


@st.cache_data(ttl=3600)
def load_snapshot() -> pd.DataFrame:
    if not SNAPSHOT_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(SNAPSHOT_PATH)


@st.cache_data(ttl=3600, show_spinner="Loading bound dataset...")
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
    errs = data_load_errors()
    if mode == "error" or errs:
        keys = ", ".join(sorted(errs.keys())) if errs else "query"
        st.warning(
            f"**Live data load failed** ({keys}). Showing sample recommendations. "
            "This is not empty usage; a query/timeout/schema error occurred. "
            "Retry later or check warehouse status."
        )
        return
    if mode == "preview":
        st.caption(
            "Showing **sample recommendations** so you can evaluate the product before "
            "connecting ACCOUNT_USAGE. Connect when an admin has granted privileges."
        )
    elif mode == "sample":
        st.caption(
            "Privileges connected, but no Cortex rows in this window yet. Sample "
            "recommendations shown. ACCOUNT_USAGE can lag ~45 minutes after new AI calls."
        )
    else:
        label = humanize_source(st.session_state.get("usage_source"))
        st.caption(f"Live Cortex metering{f' | {label}' if label else ''}.")
