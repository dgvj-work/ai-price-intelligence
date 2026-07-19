"""All SQL isolated here. App views retain up to 365 days; UI applies the day window."""

from __future__ import annotations


def _safe_days(days: int) -> int:
    """Clamp to an integer day window - never interpolate untrusted strings into SQL."""
    try:
        d = int(days)
    except (TypeError, ValueError):
        d = 90
    return max(1, min(d, 365))


def sql_cortex_spend(days: int) -> str:
    # days is sanitized to int in [1, 365] before f-string interpolation.
    d = _safe_days(days)
    return f"""
SELECT
  DATE_TRUNC('day', USAGE_TIME) AS DAY,
  FUNCTION_NAME,
  MODEL_NAME,
  SUM(COALESCE(TOKENS, 0)) AS TOKENS,
  SUM(COALESCE(TOKEN_CREDITS, 0)) AS CREDITS
FROM APP_SCHEMA.V_CORTEX_USAGE
WHERE USAGE_TIME >= DATEADD('day', -{d}, CURRENT_TIMESTAMP())
GROUP BY 1, 2, 3
ORDER BY 1
"""


def sql_cortex_top(days: int) -> str:
    d = _safe_days(days)
    return f"""
SELECT
  FUNCTION_NAME,
  MODEL_NAME,
  SUM(COALESCE(TOKEN_CREDITS, 0)) AS CREDITS,
  SUM(COALESCE(TOKENS, 0)) AS TOKENS
FROM APP_SCHEMA.V_CORTEX_USAGE
WHERE USAGE_TIME >= DATEADD('day', -{d}, CURRENT_TIMESTAMP())
GROUP BY 1, 2
ORDER BY CREDITS DESC
LIMIT 25
"""


def sql_metering_fallback(days: int) -> str:
    d = _safe_days(days)
    return f"""
SELECT
  DATE_TRUNC('day', START_TIME) AS DAY,
  SERVICE_TYPE,
  SUM(COALESCE(CREDITS_USED, 0)) AS CREDITS
FROM APP_SCHEMA.V_METERING_HISTORY
WHERE START_TIME >= DATEADD('day', -{d}, CURRENT_TIMESTAMP())
GROUP BY 1, 2
ORDER BY 1
"""


def sql_usage_by_model(days: int) -> str:
    d = _safe_days(days)
    return f"""
SELECT
  MODEL_NAME,
  FUNCTION_NAME,
  SUM(COALESCE(TOKENS, 0)) AS TOKENS,
  SUM(COALESCE(TOKEN_CREDITS, 0)) AS CREDITS
FROM APP_SCHEMA.V_CORTEX_USAGE
WHERE USAGE_TIME >= DATEADD('day', -{d}, CURRENT_TIMESTAMP())
GROUP BY 1, 2
ORDER BY CREDITS DESC
"""


SQL_ENSURE_VIEWS = "CALL APP_SCHEMA.ENSURE_ACCOUNT_USAGE_VIEWS()"

SQL_GET_CREDIT_PRICE = """
SELECT TRY_TO_DOUBLE(SETTING_VALUE) AS CREDIT_PRICE_USD
FROM APP_SCHEMA.USER_SETTINGS
WHERE SETTING_KEY = 'credit_price_usd'
LIMIT 1
"""

# Parameterized MERGE - bind key + value via Snowpark params (no float f-string).
SQL_SET_CREDIT_PRICE = """
MERGE INTO APP_SCHEMA.USER_SETTINGS t
USING (
  SELECT ? AS SETTING_KEY, ? AS SETTING_VALUE
) s
ON t.SETTING_KEY = s.SETTING_KEY
WHEN MATCHED THEN UPDATE SET
  SETTING_VALUE = s.SETTING_VALUE,
  UPDATED_AT = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (SETTING_KEY, SETTING_VALUE, UPDATED_AT)
  VALUES (s.SETTING_KEY, s.SETTING_VALUE, CURRENT_TIMESTAMP())
"""


def clamp_credit_price(price: float) -> float:
    p = float(price)
    if p < 0.01:
        return 0.01
    if p > 100.0:
        return 100.0
    return p


# Native App reference() bindings (optional Marketplace dataset)
SQL_REF_MODEL_CURRENT = """
SELECT
  MODEL_ID,
  MODEL_NAME,
  PROVIDER_NAME,
  PRICE_INPUT_USD_PER_1M_TOKENS,
  PRICE_OUTPUT_USD_PER_1M_TOKENS
FROM REFERENCE('price_intel_model_current')
ORDER BY MODEL_NAME
"""

SQL_REF_CORTEX_CURRENT = """
SELECT FUNCTION_NAME, MODEL_NAME, CREDITS_PER_1M_TOKENS
FROM REFERENCE('price_intel_cortex_current')
ORDER BY FUNCTION_NAME, MODEL_NAME
"""

SQL_REF_PRICE_CHANGES = """
SELECT
  MODEL_ID,
  CHANGED_AT,
  OLD_INPUT_USD_PER_1M,
  NEW_INPUT_USD_PER_1M,
  INPUT_PCT_CHANGE,
  OLD_OUTPUT_USD_PER_1M,
  NEW_OUTPUT_USD_PER_1M,
  OUTPUT_PCT_CHANGE
FROM REFERENCE('price_intel_price_changes')
ORDER BY CHANGED_AT DESC
LIMIT 200
"""
