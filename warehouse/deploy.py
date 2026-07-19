"""Idempotent warehouse deploy via Snowflake connector (snow CLI-compatible env)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parent / "sql"
ORDERED = [
    "00_database.sql",
    "01_tables.sql",
    "02_views.sql",
    "03_share.sql",
    "04_quality_checks.sql",
]


def _connect() -> object:
    import snowflake.connector

    account = os.environ["SNOWFLAKE_ACCOUNT"]
    user = os.environ["SNOWFLAKE_USER"]
    role = os.environ.get("SNOWFLAKE_ROLE", "AI_PRICE_ADMIN")
    warehouse = os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
    private_key_path = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH")
    if not private_key_path:
        raise SystemExit(
            "SNOWFLAKE_PRIVATE_KEY_PATH is required (key-pair auth). See docs/PUBLISHING_RUNBOOK.md"
        )

    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization

    with open(private_key_path, "rb") as f:
        passphrase = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")
        p_key = serialization.load_pem_private_key(
            f.read(),
            password=passphrase.encode() if passphrase else None,
            backend=default_backend(),
        )
    pkb = p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return snowflake.connector.connect(
        account=account,
        user=user,
        private_key=pkb,
        role=role,
        warehouse=warehouse,
    )


def _split_statements(sql: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(buf).strip().rstrip(";").strip()
            if stmt:
                parts.append(stmt)
            buf = []
    tail = "\n".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def main() -> int:
    skip_quality = "--skip-quality" in sys.argv
    conn = _connect()
    try:
        cur = conn.cursor()
        for name in ORDERED:
            if skip_quality and name == "04_quality_checks.sql":
                continue
            path = SQL_DIR / name
            print(f"==> Applying {name}")
            sql = path.read_text(encoding="utf-8")
            if name == "04_quality_checks.sql":
                # Quality checks are SELECT-only and run by refresh, not deploy.
                print("    (skipped at deploy; executed by refresh)")
                continue
            for stmt in _split_statements(sql):
                cur.execute(stmt)
        print("Warehouse deploy complete.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
