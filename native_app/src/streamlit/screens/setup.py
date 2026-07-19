"""Connect ACCOUNT_USAGE — secondary to Advisor value."""

from __future__ import annotations

import streamlit as st

from session_data import ensure_usage_views, humanize_source, needs_setup

GRANT_SQL = """\
-- ACCOUNTADMIN (or role that can grant on DATABASE SNOWFLAKE)
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO APPLICATION CORTEX_COST_ADVISOR;
"""


def render_connect_account() -> None:
    source = st.session_state.get("usage_source")
    if not needs_setup(source):
        return

    st.divider()
    st.subheader("Connect live Cortex usage")
    st.markdown(
        "Recommendations above use **sample** usage so you can evaluate the product. "
        "To rank switches on **your** models, grant read access to ACCOUNT_USAGE metering."
    )
    left, right = st.columns(2)
    with left:
        st.markdown("**Admin GRANT**")
        st.code(GRANT_SQL, language="sql")
    with right:
        st.markdown("**Then connect**")
        st.caption("Creates passthrough views inside the app. No scheduled tasks; no extra privileges.")
        if st.button("Connect live usage", type="primary", key="connect_live_usage"):
            st.cache_data.clear()
            new_source = ensure_usage_views()
            st.session_state["usage_source"] = new_source
            if needs_setup(new_source):
                st.warning("Privilege not detected yet — confirm GRANT, then try again.")
            else:
                st.success(humanize_source(new_source) or "Connected")
                st.rerun()

    with st.expander("Security — exact access"):
        st.markdown(
            """
| | |
|--|--|
| Privilege | `IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE` |
| Views | `CORTEX_AI_FUNCTIONS_USAGE_HISTORY` or `CORTEX_AISQL_USAGE_HISTORY`; AI/Cortex `METERING_HISTORY` |
| Not read | `QUERY_HISTORY`, SQL text |
| Egress | None |
| Why this privilege | Native Apps cannot take a single ACCOUNT_USAGE view grant |
            """
        )
