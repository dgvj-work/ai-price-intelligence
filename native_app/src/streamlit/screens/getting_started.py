"""In-app starter guide for Marketplace consumers after install."""

from __future__ import annotations

import streamlit as st

from screens.setup import GRANT_SQL, render_connect_account
from session_data import APP_VERSION, humanize_source, needs_setup
from theme import hero

SUPPORT_URL = "https://github.com/dgvj-work/ai-price-intelligence/discussions"
REPO_URL = "https://github.com/dgvj-work/ai-price-intelligence"


def render() -> None:
    hero(
        "Getting started",
        "Five minutes from install to ranked Cortex model-switch recommendations.",
        kicker=f"Starter guide · v{APP_VERSION}",
    )

    source = st.session_state.get("usage_source")
    preview = needs_setup(source)

    if preview:
        st.info(
            "**You are in preview mode** — Advisor shows sample recommendations so you can "
            "evaluate the product before granting privileges. Connect live usage when ready "
            "(step 2 below)."
        )
    else:
        label = humanize_source(source) or "Cortex metering"
        st.success(
            f"**Live usage connected** — reading `{label}`. "
            "Open **Advisor** for ranked switch savings on your account."
        )

    st.markdown("### 1. Open Advisor and evaluate")
    st.markdown(
        """
Use the sidebar → **Advisor**. You should see:

- A **primary recommendation** (e.g. switch model A → B and estimated credit / USD savings)
- Concentration risk, spend spikes, and a simple forward planning number
- Price-move context when public list rates overlap your usage

USD figures use the **$/credit** rate in the sidebar (your invoice rate — Snowflake does not
expose contracted prices to apps). Credits stay accurate even if the rate is approximate.
        """
    )

    st.markdown("### 2. Connect live Cortex usage (admin once)")
    if preview:
        st.markdown(
            "An **ACCOUNTADMIN** (or a role that can grant on database `SNOWFLAKE`) runs the "
            "GRANT below, then clicks **Connect live usage**. Views bind inside the app — "
            "no tasks, no egress, no `QUERY_HISTORY`."
        )
        render_connect_account()
    else:
        st.markdown(
            "Privileges are already in place. If recommendations look empty, widen the "
            "**Analysis window** in the sidebar or wait for ACCOUNT_USAGE lag (~45 minutes "
            "after new Cortex activity)."
        )
        with st.expander("GRANT SQL (reinstall / role rotation)"):
            st.code(GRANT_SQL, language="sql")
            st.caption(
                "After GRANT, reopen the app or use the sidebar **I granted privileges — connect**."
            )

    st.markdown("### 3. Set planning inputs (sidebar)")
    st.markdown(
        """
| Control | What it does |
|---------|----------------|
| **Your credit rate ($ / credit)** | Converts credit savings to USD estimates. Saved in this app’s schema for next visits. |
| **Analysis window** | 30–365 days of Cortex metering via app views. |

Wrong rate ⇒ wrong dollars; credit rankings stay usable.
        """
    )

    st.markdown("### 4. Use the pages")
    st.markdown(
        """
| Page | When to open it |
|------|-----------------|
| **Advisor** | Daily decision surface — ranked switches + risk signals |
| **Switches** | Full same-token scenario matrix for FinOps review |
| **Price Watch** | Public list-price moves on models you actually used |
| **Spend detail** | Underlying Cortex credit trend (evidence, not the product) |
| **Trust** | Privileges, architecture, honest limitations |
| **Getting started** | This guide — bookmark for new teammates |
        """
    )

    st.markdown("### 5. Optional — live pricing enrichment")
    st.markdown(
        """
For live public list rates instead of the bundled snapshot, bind the companion Marketplace
dataset **AI Model & Compute Price Intelligence** reference views (see listing docs / repo README).
The app works without this — Price Watch falls back to the packaged snapshot.
        """
    )

    with st.expander("Quick FAQ"):
        st.markdown(
            f"""
**Do I need to refresh data?**  
No. Passthrough views rebind on session start. Reopen the app after new Cortex activity.

**Why `IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE`?**  
Native Apps cannot take a grant on a single ACCOUNT_USAGE view. The app only reads Cortex /
AI metering views (never `QUERY_HISTORY` or SQL text). Details on **Trust**.

**Who is this for?**  
FinOps / platform engineers deciding which Cortex models to allow or migrate.

**Support**  
[GitHub Discussions]({SUPPORT_URL}) · [Source]({REPO_URL}) · v{APP_VERSION}
            """
        )

    st.caption(
        "Tip: share this **Getting started** tab with anyone who installs the app — "
        "all setup steps live here."
    )
