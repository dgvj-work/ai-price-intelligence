"""SCD2 merge logic tests (≥85% coverage target)."""

from __future__ import annotations

from datetime import datetime

from ingestion.scd2 import (
    Scd2Row,
    business_hash,
    cortex_price_hash,
    gpu_price_hash,
    merge_scd2,
    model_price_hash,
)


def test_business_hash_stable() -> None:
    a = business_hash({"b": 2, "a": 1})
    b = business_hash({"a": 1, "b": 2})
    assert a == b
    assert a != business_hash({"a": 1, "b": 3})


def test_merge_inserts_new() -> None:
    as_of = datetime(2026, 7, 1)
    cs = merge_scd2(
        existing_current={},
        incoming={"m1": ("payload", "hash1")},
        as_of=as_of,
    )
    assert cs.close_keys == []
    assert len(cs.insert_rows) == 1
    assert cs.insert_rows[0].natural_key == "m1"
    assert cs.insert_rows[0].is_current is True
    assert cs.insert_rows[0].valid_from == as_of


def test_merge_unchanged() -> None:
    as_of = datetime(2026, 7, 8)
    existing = {
        "m1": Scd2Row(
            natural_key="m1",
            payload="old",
            row_hash="hash1",
            valid_from=datetime(2026, 7, 1),
            valid_to=None,
            is_current=True,
        )
    }
    cs = merge_scd2(
        existing_current=existing,
        incoming={"m1": ("old", "hash1")},
        as_of=as_of,
    )
    assert cs.close_keys == []
    assert cs.insert_rows == []
    assert cs.unchanged_keys == ["m1"]


def test_merge_closes_and_opens_on_change() -> None:
    as_of = datetime(2026, 7, 8)
    existing = {
        "m1": Scd2Row(
            natural_key="m1",
            payload="old",
            row_hash="hash1",
            valid_from=datetime(2026, 7, 1),
            valid_to=None,
            is_current=True,
        )
    }
    cs = merge_scd2(
        existing_current=existing,
        incoming={"m1": ("new", "hash2")},
        as_of=as_of,
    )
    assert cs.close_keys == ["m1"]
    assert len(cs.insert_rows) == 1
    assert cs.insert_rows[0].row_hash == "hash2"
    assert cs.insert_rows[0].payload == "new"


def test_price_hash_helpers() -> None:
    h1 = model_price_hash(2.5, 10.0, 1.25, 50.0)
    h2 = model_price_hash(2.5, 10.0, 1.25, 50.0)
    h3 = model_price_hash(2.5, 10.0, 1.25, None)
    assert h1 == h2
    assert h1 != h3
    assert gpu_price_hash(1.0, 0.5, 0.8) != gpu_price_hash(1.0, None, 0.8)
    assert cortex_price_hash(1.21) == cortex_price_hash(1.21)
