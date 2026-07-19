"""Connect-your-account guidance — never the only thing on screen."""

from __future__ import annotations

import streamlit as st

from session_data import ensure_usage_views, humanize_source, needs_setup


GRANT_SQL = """\
-- Run as ACCOUNTADMIN (or a role that can grant on DATABASE SNOWFLAKE)
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO APPLICATION CORTEX_COST_ADVISOR;
"""


def render_connect_account() -> None:
    """Calm, actionable connect section when privileges are not yet granted."""
    source = st.session_state.get("usage_source")
    if not needs_setup(source):
        return

    st.divider()
    st.subheader("Connect your account (one admin step)")
    st.markdown(
        """
Preview charts above use **sample data**. To see **your** Cortex spend and power
Model Advisor / Price Watch from real usage, an account admin grants read access
to Snowflake’s metering views — then click **Connect**.
        """
    )

    step1, step2 = st.columns(2)
    with step1:
        st.markdown("**1. Grant privilege**")
        st.caption("Snowsight → this app → Privileges → grant Imported privileges on SNOWFLAKE, or run:")
        st.code(GRANT_SQL, language="sql")
    with step2:
        st.markdown("**2. Connect**")
        st.caption(
            "Creates read-only views inside the app. Safe to re-run. "
            "ACCOUNT_USAGE can lag live Cortex calls by up to ~45 minutes."
        )
        if st.button("Connect live usage", type="primary", key="connect_live_usage"):
            st.cache_data.clear()
            new_source = ensure_usage_views()
            st.session_state["usage_source"] = new_source
            if needs_setup(new_source):
                st.warning(
                    "Privilege not detected yet. Confirm the GRANT as ACCOUNTADMIN, "
                    "wait a few seconds, then click Connect again."
                )
            else:
                st.success(
                    "Connected — "
                    + (humanize_source(new_source) or "live metering available")
                    + ". Reloading…"
                )
                st.rerun()

    with st.expander("Security details — what this grant allows"):
        st.markdown(
            """
| Topic | Detail |
|-------|--------|
| **Privilege** | `IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE` |
| **Views read** | `CORTEX_AI_FUNCTIONS_USAGE_HISTORY` (preferred) or `CORTEX_AISQL_USAGE_HISTORY`; AI/Cortex rows in `METERING_HISTORY` |
| **Not read** | `QUERY_HISTORY`, SQL text, your business tables |
| **Egress** | None — no network, external access, containers, or telemetry |
| **Writes** | Only inside the app’s own schema |
| **Why not narrower?** | Native Apps cannot be granted a single ACCOUNT_USAGE view; this is Snowflake’s documented mechanism |

Full trust matrix: **About / Trust**.
            """
        )
