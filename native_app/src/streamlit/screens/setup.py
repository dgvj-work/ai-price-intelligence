"""Post-install setup guidance shown when ACCOUNT_USAGE access is not ready."""

from __future__ import annotations

import streamlit as st

from session_data import ensure_usage_views, humanize_source, needs_setup


GRANT_SQL = """\
-- Run as ACCOUNTADMIN (or a role that can grant on the SNOWFLAKE database)
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO APPLICATION CORTEX_COST_ADVISOR;
"""


def render_setup_panel(*, compact: bool = False) -> bool:
    """
    Guided configure experience for first-run / missing privileges.

    Returns True when the panel was shown (caller should usually stop rendering
    data-dependent content).
    """
    source = st.session_state.get("usage_source")
    if not needs_setup(source):
        return False

    st.subheader("Configure Cortex Cost Advisor")
    if not compact:
        st.markdown(
            """
This app stays entirely inside your Snowflake account. To show **your** Cortex /
AI spend, an account admin must grant read access to Snowflake’s ACCOUNT_USAGE
metering views — the same pattern used by other FinOps / cost Native Apps.
            """
        )

    st.markdown("#### What you’ll unlock")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Overview**")
        st.caption("Credits, USD estimate, and spend trend for Cortex / AI functions.")
    with c2:
        st.markdown("**Model Advisor**")
        st.caption("Compare your token volumes against alternate Cortex model rates.")
    with c3:
        st.markdown("**Price Watch**")
        st.caption("Flag list-price moves that affect models you already use.")

    st.markdown("#### Setup steps")
    st.markdown(
        """
1. Open this app in Snowsight → **Privileges** (or Security), and grant  
   **Imported privileges on the SNOWFLAKE database**.  
   Or run the SQL below as `ACCOUNTADMIN`.
2. Click **Configure** below to create the usage views.
3. Wait a few minutes if you just started using Cortex — ACCOUNT_USAGE can lag  
   by up to ~45 minutes.
        """
    )

    with st.expander("Admin SQL (copy / paste)", expanded=True):
        st.code(GRANT_SQL, language="sql")

    with st.expander("Why this privilege? (security)"):
        st.markdown(
            """
**What it allows:** read-only access to ACCOUNT_USAGE views needed for Cortex /
AI metering (`CORTEX_AI_FUNCTIONS_USAGE_HISTORY` or `CORTEX_AISQL_USAGE_HISTORY`,
plus AI-related rows in `METERING_HISTORY`).

**What it does not allow:** the app never reads `QUERY_HISTORY` or SQL text,
never writes outside its own schema, and never calls the public internet.

**Why not a narrower grant?** Snowflake’s Native App model exposes this as the
`IMPORTED PRIVILEGES ON SNOWFLAKE DB` privilege. There is no supported way to
grant a single ACCOUNT_USAGE view to an application; the privilege is the
documented, audit-friendly mechanism. Your org can review the un-obfuscated
setup script and Streamlit source before granting.
            """
        )

    col_a, col_b = st.columns([1, 2])
    with col_a:
        if st.button("Configure", type="primary", use_container_width=True):
            st.cache_data.clear()
            new_source = ensure_usage_views()
            st.session_state["usage_source"] = new_source
            if needs_setup(new_source):
                st.error(
                    "Still waiting on privileges or live usage data. "
                    "Confirm the grant, then try Configure again. "
                    f"({humanize_source(new_source) or 'not ready'})"
                )
            else:
                st.success(
                    f"Configured — reading {humanize_source(new_source)}."
                )
                st.rerun()
    with col_b:
        st.caption(
            "Safe to re-run anytime. If Cortex isn’t enabled yet, Overview stays empty "
            "until AI functions produce ACCOUNT_USAGE rows."
        )

    return True
