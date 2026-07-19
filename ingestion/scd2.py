"""Generic SCD Type 2 merge logic for price history.

Never mutates closed history rows. Opens a new current row only when the
business hash of tracked price fields changes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generic, TypeVar

T = TypeVar("T")


def business_hash(payload: dict[str, Any]) -> str:
    """Stable hash of tracked fields (sorted JSON, compact separators)."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Scd2Row(Generic[T]):
    natural_key: str
    payload: T
    row_hash: str
    valid_from: datetime
    valid_to: datetime | None
    is_current: bool


@dataclass
class Scd2ChangeSet(Generic[T]):
    close_keys: list[str]
    insert_rows: list[Scd2Row[T]]
    unchanged_keys: list[str]


def merge_scd2(
    *,
    existing_current: dict[str, Scd2Row[T]],
    incoming: dict[str, tuple[T, str]],
    as_of: datetime,
) -> Scd2ChangeSet[T]:
    """Compare incoming natural_key -> (payload, hash) against current rows.

    Returns keys to close (set is_current=False, valid_to=as_of) and new rows
    to insert. Unchanged keys are reported but not written.
    """
    close_keys: list[str] = []
    insert_rows: list[Scd2Row[T]] = []
    unchanged: list[str] = []

    for key, (payload, new_hash) in incoming.items():
        current = existing_current.get(key)
        if current is None:
            insert_rows.append(
                Scd2Row(
                    natural_key=key,
                    payload=payload,
                    row_hash=new_hash,
                    valid_from=as_of,
                    valid_to=None,
                    is_current=True,
                )
            )
            continue
        if current.row_hash == new_hash:
            unchanged.append(key)
            continue
        close_keys.append(key)
        insert_rows.append(
            Scd2Row(
                natural_key=key,
                payload=payload,
                row_hash=new_hash,
                valid_from=as_of,
                valid_to=None,
                is_current=True,
            )
        )

    return Scd2ChangeSet(
        close_keys=close_keys,
        insert_rows=insert_rows,
        unchanged_keys=unchanged,
    )


def model_price_hash(
    price_input: float | None,
    price_output: float | None,
    price_cached: float | None,
    batch_discount_pct: float | None,
) -> str:
    return business_hash(
        {
            "price_input_usd_per_1m_tokens": price_input,
            "price_output_usd_per_1m_tokens": price_output,
            "price_cached_input_usd_per_1m_tokens": price_cached,
            "batch_discount_pct": batch_discount_pct,
        }
    )


def gpu_price_hash(
    on_demand: float | None,
    spot: float | None,
    reserved: float | None,
) -> str:
    return business_hash(
        {
            "price_on_demand_usd_hr": on_demand,
            "price_spot_usd_hr": spot,
            "price_1yr_reserved_usd_hr": reserved,
        }
    )


def cortex_price_hash(credits_per_1m_tokens: float) -> str:
    return business_hash({"credits_per_1m_tokens": credits_per_1m_tokens})
