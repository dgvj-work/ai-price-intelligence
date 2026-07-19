"""Shared data helpers for Streamlit screens (not under pages/ - avoids multipage clash)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import pandas as pd
import streamlit as st

import demo_data
import queries

SNAPSHOT_PATH = Path(__file__).resolve().parent / "data" / "price_snapshot.csv"

APP_VERSION = "1.2.6"  # keep in sync with manifest.yml version.label

# Single source of truth for consumer-facing support links.
SUPPORT_URL = "https://github.com/dgvj-work/ai-price-intelligence/discussions"
REPO_URL = "https://github.com/dgvj-work/ai-price-intelligence"
SUPPORT_EMAIL = "digvijay.vaghela@yahoo.com"

# Internal procedure return values -> never shown raw in the UI.
_LIVE_SOURCES = {
    "CORTEX_AI_FUNCTIONS_USAGE_HISTORY": "Cortex AI Functions usage history",
    "CORTEX_AISQL_USAGE_HISTORY": "Cortex AI SQL usage history",
}
_PENDING = frozenset({"PENDING_PRIVILEGES", "EMPTY_STUB"})
_BLOCKED_UI_TOKENS = ("EMPTY_STUB", "PENDING_PRIVILEGES", "ENSURE_FAILED")

# live = real ACCOUNT_USAGE rows
# preview = privileges missing - sample data + connect CTA
# sample = privileges OK but no rows in window - sample data, no connect CTA
# error = live query failed - sample shown with warning
DataMode = Literal["live", "preview", "sample", "error"]

GRANT_SQL = (
    "GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE "
    "TO APPLICATION CORTEX_COST_ADVISOR;"
)


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
        return "PENDING_PRIVILEGES"
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


def connection_status_label(source: str | None) -> str:
    """Short human status for sidebar / Getting started."""
    if not needs_setup(source):
        label = humanize_source(source) or "Cortex metering"
        return f"Live · {label}"
    token = sanitize_source_token(source)
    if token == "ENSURE_FAILED":
        return "Connect failed · procedure error"
    return "Preview · sample data (not live yet)"


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
        record_diagnostic("load_error", f"{key}:{message[:200]}")
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
    except Exception as exc:  # noqa: BLE001
        record_diagnostic("ensure_failed", f"{type(exc).__name__}:{exc}")
        return "ENSURE_FAILED"


def connect_live_usage() -> dict[str, Any]:
    """
    Rebind ACCOUNT_USAGE views and record a clear connect attempt for the UI.

    Returns a small dict: connected (bool), source, message.
    Does not grant privileges (apps cannot self-grant IMPORTED PRIVILEGES).
    """
    st.cache_data.clear()
    source = ensure_usage_views()
    st.session_state["usage_source"] = source
    connected = not needs_setup(source)
    if connected:
        label = humanize_source(source) or "Cortex metering"
        message = f"Connected to live usage ({label}). Recommendations now use your account."
    elif sanitize_source_token(source) == "ENSURE_FAILED":
        message = (
            "Connect failed while creating app views. Check warehouse status, "
            "then try again. If it persists, open Getting started."
        )
    else:
        message = (
            "Still on preview sample. The app does not have "
            "IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE yet. "
            "Run the GRANT in a Worksheet as ACCOUNTADMIN, then click Connect again."
        )
    result = {
        "connected": connected,
        "source": source,
        "message": message,
    }
    st.session_state["last_connect_result"] = result
    return result


def last_connect_result() -> dict[str, Any] | None:
    raw = st.session_state.get("last_connect_result")
    return dict(raw) if isinstance(raw, dict) else None


def init_usage_session(*, force: bool = False) -> None:
    """Auto-refresh usage views once per browser session (and on force)."""
    if force or "usage_source" not in st.session_state:
        st.session_state["usage_source"] = ensure_usage_views()
    st.session_state["usage_source"] = sanitize_source_token(
        st.session_state.get("usage_source")
    )


def _persist_setting(key: str, value: str) -> None:
    session = _session()
    if session is None:
        return
    try:
        session.sql(queries.SQL_SET_SETTING, params=[key, value]).collect()
    except Exception:  # noqa: BLE001
        safe_key = key.replace("'", "")
        safe_val = value.replace("'", "")
        try:
            session.sql(
                f"""
                MERGE INTO APP_SCHEMA.USER_SETTINGS t
                USING (SELECT '{safe_key}' AS SETTING_KEY) s
                ON t.SETTING_KEY = s.SETTING_KEY
                WHEN MATCHED THEN UPDATE SET
                  SETTING_VALUE = '{safe_val}',
                  UPDATED_AT = CURRENT_TIMESTAMP()
                WHEN NOT MATCHED THEN INSERT (SETTING_KEY, SETTING_VALUE, UPDATED_AT)
                  VALUES ('{safe_key}', '{safe_val}', CURRENT_TIMESTAMP())
                """
            ).collect()
        except Exception:  # noqa: BLE001
            pass


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
    p = queries.clamp_credit_price(price)
    _persist_setting("credit_price_usd", f"{p:.4f}")


def load_persisted_min_savings_pct(default: float = 15.0) -> float:
    """Return UI percent (e.g. 15.0 for 15%), not fraction."""
    session = _session()
    if session is None:
        return default
    try:
        rows = session.sql(
            queries.SQL_GET_SETTING, params=["min_switch_savings_pct"]
        ).collect()
        if rows and rows[0][0] is not None:
            return queries.clamp_min_savings_pct(float(rows[0][0]))
    except Exception:  # noqa: BLE001
        pass
    return default


def persist_min_savings_pct(pct: float) -> None:
    p = queries.clamp_min_savings_pct(pct)
    _persist_setting("min_switch_savings_pct", f"{p:.2f}")


def record_diagnostic(event_type: str, detail: str) -> str | None:
    """Log to APP_SCHEMA.DIAGNOSTICS (consumer account only; no egress)."""
    session = _session()
    code = f"CCA-{APP_VERSION}-{event_type[:32]}"
    payload = f"{code}|{detail}"[:900]
    st.session_state["last_diagnostic"] = payload
    if session is None:
        return payload
    try:
        session.sql(
            queries.SQL_INSERT_DIAGNOSTIC,
            params=[event_type[:64], payload],
        ).collect()
    except Exception:  # noqa: BLE001
        pass
    return payload


def last_diagnostic() -> str | None:
    cached = st.session_state.get("last_diagnostic")
    if cached:
        return str(cached)
    session = _session()
    if session is None:
        return None
    try:
        rows = session.sql(queries.SQL_LATEST_DIAGNOSTIC).collect()
        if rows and rows[0][3] is not None:
            return str(rows[0][3])
    except Exception:  # noqa: BLE001
        pass
    return None


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
        diag = last_diagnostic()
        if diag:
            st.code(diag, language=None)
            st.caption(
                "Copy the diagnostic string into a GitHub Discussion if you need help. "
                "It stays in this app schema only (no external telemetry)."
            )
        return
    if mode == "preview":
        st.info(
            "**Preview mode (sample data).** Numbers and recommendations are synthetic "
            "so you can evaluate the product. They are **not** your account spend. "
            "To go live: ACCOUNTADMIN runs the GRANT on Getting started, then click "
            "**Connect live usage** (sidebar or below)."
        )
        attempt = last_connect_result()
        if attempt and not attempt.get("connected"):
            st.warning(attempt.get("message") or "Connect did not find privileges yet.")
    elif mode == "sample":
        st.caption(
            "Privileges connected, but no Cortex rows in this window yet. Sample "
            "recommendations/charts shown. ACCOUNT_USAGE can lag ~45 minutes after new AI calls."
        )
    else:
        label = humanize_source(st.session_state.get("usage_source"))
        st.caption(
            f"Live Cortex metering{f' | {label}' if label else ''}. "
            "Charts and recommendations use your account data for this window."
        )
