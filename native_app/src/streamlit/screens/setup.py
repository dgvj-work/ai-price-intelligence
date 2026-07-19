"""Connect ACCOUNT_USAGE - secondary to Advisor value."""

from __future__ import annotations

import streamlit as st

from session_data import (
    GRANT_SQL as GRANT_ONE_LINER,
    connect_live_usage,
    last_connect_result,
    needs_setup,
)

GRANT_SQL = f"""\
-- ACCOUNTADMIN (or a role that can grant on DATABASE SNOWFLAKE)
-- Required once for live Cortex metering. Rename the app if you installed under another name.
-- This is the only database-level privilege the app needs. No grants on your DBs/schemas/tables.
{GRANT_ONE_LINER}
"""


def render_connect_account(*, compact: bool = False) -> None:
    source = st.session_state.get("usage_source")
    if not needs_setup(source):
        return

    st.divider()
    st.subheader("Connect live Cortex usage")
    st.markdown(
        "Recommendations above use **sample** usage so you can evaluate the product. "
        "The Connect button only **rebinds views after** an admin GRANT. "
        "It cannot grant privileges by itself."
    )

    attempt = last_connect_result()
    if attempt and not attempt.get("connected"):
        st.warning(attempt["message"])

    left, right = st.columns(2)
    with left:
        st.markdown("**Step 1 — Admin GRANT** (Worksheet as ACCOUNTADMIN)")
        st.code(GRANT_ONE_LINER if compact else GRANT_SQL, language="sql")
        st.caption(
            "Open Projects -> Worksheets, set role to **ACCOUNTADMIN**, run the GRANT, "
            "then come back here. Being ACCOUNTADMIN on the app page is not the same as "
            "running the GRANT in a worksheet."
        )
    with right:
        st.markdown("**Step 2 — Connect in this app**")
        st.caption(
            "Creates passthrough views inside the app. No scheduled tasks; no extra privileges."
        )
        if st.button("Connect live usage", type="primary", key="connect_live_usage"):
            result = connect_live_usage()
            if result["connected"]:
                st.success(result["message"])
                st.rerun()
            else:
                st.error(result["message"])
                st.code(GRANT_ONE_LINER, language="sql")

    with st.expander("Security: exact access"):
        st.markdown(
            """
| | |
|--|--|
| Privilege | **IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE** -> application |
| Database / schema | **SNOWFLAKE**.**ACCOUNT_USAGE** only (via imported privileges) |
| Views read | **CORTEX_AI_FUNCTIONS_USAGE_HISTORY** (preferred), **CORTEX_AISQL_USAGE_HISTORY** (fallback), **METERING_HISTORY** (AI/Cortex rows) |
| Your DBs / schemas / tables | **No grants required or used** |
| Not read | **QUERY_HISTORY**, SQL text, stages |
| Egress / tasks / SPCS | None |
| Why this privilege | Native Apps cannot take a single ACCOUNT_USAGE view grant |
| Details | Full matrix on **Getting started** |
            """
        )
