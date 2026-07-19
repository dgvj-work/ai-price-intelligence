"""Canonical model-id matching — avoids loose substring false positives."""

from __future__ import annotations

import re


def normalize_model_id(name: str) -> str:
    """Lowercase, unify separators, drop noise tokens."""
    s = str(name or "").lower().strip()
    s = s.replace("_", "-")
    s = re.sub(r"[^a-z0-9.\-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-.")
    return s


def models_match(used: str, candidate: str) -> bool:
    """
    True when used usage model and a price-row id refer to the same model.

    - Exact match after normalize, or
    - Prefix match only if the shorter id is ≥ 10 chars and the longer continues
      with a separator (avoids 'llama' matching 'llama3.1-405b').
    """
    u = normalize_model_id(used)
    c = normalize_model_id(candidate)
    if not u or not c:
        return False
    if u == c:
        return True
    shorter, longer = (u, c) if len(u) <= len(c) else (c, u)
    if len(shorter) < 10:
        return False
    if not longer.startswith(shorter):
        return False
    if len(longer) == len(shorter):
        return True
    return longer[len(shorter)] in "-."


def overlaps_used(candidate: str, used_models: set[str]) -> bool:
    if not used_models:
        return False
    return any(models_match(m, candidate) for m in used_models)
