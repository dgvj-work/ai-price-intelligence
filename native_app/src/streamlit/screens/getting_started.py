"""In-app starter guide for Marketplace consumers after install."""

from __future__ import annotations

import streamlit as st

from screens.setup import GRANT_SQL, render_connect_account
from session_data import (
    APP_VERSION,
    REPO_URL,
    SUPPORT_EMAIL,
    SUPPORT_URL,
    humanize_source,
    needs_setup,
)
from theme import hero, panel, section

# Exact ACCOUNT_USAGE objects the setup procedure wraps (read-only via imported privileges).
ACCOUNT_USAGE_OBJECTS = """\
SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY   -- preferred
SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AISQL_USAGE_HISTORY          -- fallback if preferred missing
SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY                    -- AI_SERVICES / Cortex rows only
"""

OPTIONAL_BIND_SQL = """\
-- After installing AI Model & Compute Price Intelligence, bind in Snowsight:
--   App -> Security / References (or Connections) -> set each reference below.
-- Or use ALTER APPLICATION ... SET REFERENCES (account-specific syntax varies by UI).
--
-- Reference name                     -> Consumer view (from the data listing)
-- price_intel_model_current          -> <PRICE_DB>.SHARE.VW_MODEL_CURRENT
-- price_intel_cortex_current         -> <PRICE_DB>.SHARE.VW_CORTEX_CURRENT
-- price_intel_price_changes          -> <PRICE_DB>.SHARE.VW_PRICE_CHANGES_90D
--
-- Privilege required on each bound view: SELECT only.
-- Replace <PRICE_DB> with the database name created when you installed the listing.
"""


def render() -> None:
    hero(
        "Getting started",
        "From install to first recommendations: privileges, optional binds, warehouse, and every page.",
        kicker=f"Starter guide | v{APP_VERSION}",
    )

    source = st.session_state.get("usage_source")
    preview = needs_setup(source)

    with panel():
        if preview:
            st.info(
                "**Preview mode.** Advisor uses sample recommendations so you can evaluate "
                "before any privilege grant. Complete **section 2 (Required privileges)** when ready for live data."
            )
        else:
            label = humanize_source(source) or "Cortex metering"
            st.success(
                f"**Live usage connected.** Reading `{label}`. "
                "Optional price-dataset binds are still available under section 6."
            )

    section("Privilege map", "Required vs optional vs automatic vs never requested.")
    st.markdown(
        """
| Layer | What you grant | Required? | Who runs it |
|-------|----------------|-----------|-------------|
| **Snowflake shared DB** | `IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE` **to the application** | **Yes** (for live usage) | `ACCOUNTADMIN` (or a role that can grant on `SNOWFLAKE`) |
| **Your databases / schemas / tables** | Nothing | No | - |
| **App schema objects** | Nothing (granted to application role `APP_USER` at install) | Automatic | Setup script |
| **Query warehouse** | `USAGE` on a warehouse for the role opening Streamlit | Yes (to run the UI) | Platform admin |
| **Price Intelligence listing** | Install listing + bind 3 views (`SELECT` via references) | Optional | Admin who installed the data listing |
| **Network / external access / tasks** | Nothing requested | Never | - |

Native Apps **cannot** accept a grant on a single `ACCOUNT_USAGE` view. The one
`IMPORTED PRIVILEGES` grant is the supported Snowflake pattern. This app only
**reads** the Cortex / AI metering objects listed below. Never `QUERY_HISTORY`,
never SQL text, never your business tables.
        """
    )

    section("1. Evaluate in preview", "No grants needed yet.")
    st.markdown(
        """
Open sidebar -> **Advisor**. You should already see:

- A **primary recommendation** (model switch + estimated credit / USD savings)
- Concentration risk, spend spikes, and a simple forward planning number
- Price-move context from the **bundled** snapshot (until optional binds are set)

No database, schema, or table privileges are needed for preview.
        """
    )

    section("2. Required: connect live Cortex usage", "One grant unlocks live metering.")
    st.caption("Replace the application name if you renamed it at install.")
    if preview:
        render_connect_account()
    else:
        st.code(GRANT_SQL, language="sql")
        st.caption(
            "Already connected. After reinstall or role changes, re-run the GRANT, then use "
            "sidebar **I granted privileges; connect**, or reopen the app."
        )

    with st.expander("What that GRANT actually unlocks (exact objects)", expanded=preview):
        st.markdown(
            """
The setup procedure creates **passthrough views inside the app**
(`APP_SCHEMA.V_CORTEX_USAGE`, `APP_SCHEMA.V_METERING_HISTORY`) that select from:
            """
        )
        st.code(ACCOUNT_USAGE_OBJECTS, language="sql")
        st.markdown(
            """
| Topic | Detail |
|-------|--------|
| Database | `SNOWFLAKE` (Snowflake-owned shared database) |
| Schema | `ACCOUNT_USAGE` |
| Objects | Three views above only (via imported privileges) |
| Window | Last **365 days** (UI can narrow to 30-365) |
| Writes | **None** outside `APP_SCHEMA` |
| Consumer DBs | **No** `USAGE` / `SELECT` on your databases, schemas, or tables |
| Not read | `QUERY_HISTORY`, session history, SQL text, stage files |

You do **not** run separate `GRANT SELECT ON VIEW ...` statements for those
`ACCOUNT_USAGE` views. Imported privileges cover them for the application.
            """
        )

    with st.expander("Verify the privilege after GRANT"):
        st.code(
            """\
-- As ACCOUNTADMIN (or a role that can see grants on the app)
SHOW GRANTS TO APPLICATION CORTEX_COST_ADVISOR;

-- You should see IMPORTED PRIVILEGES on DATABASE SNOWFLAKE (wording may vary).
-- Then open this app and click "Connect live usage" (or reopen the session).
""",
            language="sql",
        )

    section("3. Who can open the app + warehouse")
    st.markdown(
        """
| Item | What consumers need |
|------|---------------------|
| **Application role** | Install grants application role **`APP_USER`** access to the Streamlit UI and app views. In Snowsight, grant that application role to the Snowflake roles/users who should open the app (Security -> Privileges / Roles, wording varies by UI). |
| **No extra object grants** | End users do **not** need `SELECT` on `SNOWFLAKE.ACCOUNT_USAGE.*` themselves. The **application** holds imported privileges and exposes thin views to `APP_USER`. |
| **Warehouse** | Streamlit needs a query warehouse. In Snowsight, set a warehouse on the app (or ensure the user's default role has `USAGE` on a warehouse). Without it the UI may fail to load data. |
| **Credits** | Queries run in **your** account warehouse (normal compute billing). |
        """
    )

    with st.expander("Objects created inside the app (automatic; do not grant these yourself)"):
        st.markdown(
            """
Created by the install setup script and granted to application role **`APP_USER`**:

| Object | Privileges to `APP_USER` | Purpose |
|--------|--------------------------|---------|
| Schema `APP_SCHEMA` | `USAGE` | App container |
| Streamlit `APP_SCHEMA.CORTEX_COST_ADVISOR` | `USAGE` | UI entrypoint |
| Procedure `ENSURE_ACCOUNT_USAGE_VIEWS()` | `USAGE` | Rebuild passthrough views after GRANT |
| Procedure `REGISTER_REFERENCE(...)` | `USAGE` | Optional Marketplace view binds |
| View `V_CORTEX_USAGE` | `SELECT` | Cortex token / credit usage |
| View `V_METERING_HISTORY` | `SELECT` | AI / Cortex metering rollup |
| Table `USER_SETTINGS` | `SELECT`, `INSERT`, `UPDATE` | Your $/credit preference (stays in-app) |

These live **inside the application**. Consumers never create them manually and
never grant consumer-table access to the app.
            """
        )

    section("4. Set planning inputs", "Sidebar controls that shape USD estimates and window size.")
    st.markdown(
        """
| Control | What it does | Privilege needed |
|---------|--------------|------------------|
| **Your credit rate ($ / credit)** | Converts savings to USD estimates; persisted in `APP_SCHEMA.USER_SETTINGS` | None beyond app access |
| **Analysis window** | 30-365 days of metering via app views | None beyond the section 2 GRANT for live data |

Wrong rate => wrong dollars; credit rankings stay usable. Snowflake does **not**
expose your contracted credit price to apps.
        """
    )

    section("5. Use the pages")
    st.markdown(
        """
| Page | When to open it |
|------|-----------------|
| **Getting started** | This guide. Share with every installer |
| **Advisor** | Daily decisions: ranked switches + risk signals |
| **Switches** | Full same-token scenario matrix for FinOps review |
| **Price Watch** | Public list-price moves on models you used |
| **Spend detail** | Underlying Cortex credit trend (evidence) |
| **Trust** | Security posture, architecture, limitations |
        """
    )

    section("6. Optional: bind Price Intelligence views")
    st.markdown(
        """
For **live** public list rates (instead of the bundled CSV snapshot):

1. Install the companion Marketplace listing **AI Model & Compute Price Intelligence**
   in the same account (creates a database with a `SHARE` schema of secure views).
2. In Snowsight, open **this app -> Security / References** (or Connections) and bind
   each reference to the matching view. Privilege on each bind: **`SELECT` only**.
        """
    )
    st.markdown(
        """
| App reference (manifest) | Bind to view | Privilege |
|--------------------------|--------------|-----------|
| `price_intel_model_current` | `<PRICE_DB>.SHARE.VW_MODEL_CURRENT` | `SELECT` |
| `price_intel_cortex_current` | `<PRICE_DB>.SHARE.VW_CORTEX_CURRENT` | `SELECT` |
| `price_intel_price_changes` | `<PRICE_DB>.SHARE.VW_PRICE_CHANGES_90D` | `SELECT` |
        """
    )
    st.code(OPTIONAL_BIND_SQL, language="sql")
    st.caption(
        "Replace `<PRICE_DB>` with the database name from the data listing install. "
        "If unbound, Advisor / Price Watch still work using the packaged snapshot."
    )

    with st.expander("Full permission checklist (copy for security review)"):
        st.markdown(
            f"""
#### Required for live recommendations

```sql
-- ACCOUNTADMIN (or equivalent)
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE
  TO APPLICATION CORTEX_COST_ADVISOR;
```

Then: open app -> **Connect live usage** (or reopen session).

#### Required for any user to run the UI

- Application role `APP_USER` available to their Snowflake role (via install / Snowsight).
- `USAGE` on a warehouse used as the Streamlit query warehouse.

#### Optional enrichment

- Install AI Model & Compute Price Intelligence listing.
- Bind three references above (`SELECT` on each `SHARE.VW_*` view).

#### Explicitly NOT required / NOT requested

| Item | Status |
|------|--------|
| `GRANT` on your databases / schemas / tables | Not used |
| `GRANT SELECT` on individual `ACCOUNT_USAGE` views | Not supported for Native Apps; covered by imported privileges |
| `QUERY_HISTORY` / sensitive query text | Never read |
| External access integrations / network egress | None |
| `CREATE TASK` / `EXECUTE TASK` | None |
| SPCS / compute pools | None |
| Secrets / API keys | None |

Version: **v{APP_VERSION}** | Support: [GitHub Discussions]({SUPPORT_URL}) | [Source]({REPO_URL})
            """
        )

    with st.expander("Troubleshooting"):
        st.markdown(
            """
| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Advisor stays on sample / "preview" | `IMPORTED PRIVILEGES` missing or not yet connected | Re-run section 2 GRANT -> **Connect live usage** |
| Connect button still fails | Wrong app name in GRANT, or role lacks grant rights on `SNOWFLAKE` | Confirm app name; use `ACCOUNTADMIN` |
| UI loads but queries error | No warehouse / no warehouse `USAGE` | Set Streamlit warehouse in Snowsight |
| Empty recommendations after connect | No Cortex usage in the window, or ACCOUNT_USAGE lag | Widen window; wait ~45 minutes after AI calls |
| Price Watch looks stale | Optional references unbound | Bind section 6 views, or accept bundled snapshot |
| Teammate cannot open app | Missing application role | Grant app role `APP_USER` to their Snowflake role |
            """
        )

    section("Stay updated (optional)")
    with panel():
        st.caption(
            "This app has no network egress, so it cannot phone home. "
            "If you want product updates or to share feedback, reach out directly:"
        )
        c1, c2 = st.columns(2)
        with c1:
            st.link_button(
                "GitHub Discussions",
                SUPPORT_URL,
                use_container_width=True,
            )
        with c2:
            st.link_button(
                "Email publisher",
                f"mailto:{SUPPORT_EMAIL}?subject=Cortex%20Cost%20Advisor%20-%20hello",
                use_container_width=True,
            )
        st.markdown(f"Contact: [{SUPPORT_EMAIL}](mailto:{SUPPORT_EMAIL})")
        st.caption(
            "Tip for FinOps teams: say which company/account you installed on. "
            "That helps prioritize features. Marketplace install analytics also appear "
            "for the publisher in Snowflake Provider Studio after the listing is live."
        )

    st.caption(
        "Bookmark **Getting started** for new teammates. Every privilege and bind lives here."
    )
