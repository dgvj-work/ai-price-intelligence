"""Optional Hugging Face leaderboard enrichment (public endpoints).

Seeds remain authoritative. Failures here never fail the refresh.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from ingestion.models import BenchmarkSeed, ScoreType

logger = logging.getLogger(__name__)

# Open LLM Leaderboard results dataset (public)
HF_DATASET_URL = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=open-llm-leaderboard/contents&config=default&split=train&offset=0&length=100"
)
SOURCE_URL = "https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard"


@retry(stop=stop_after_attempt(2), wait=wait_exponential_jitter(initial=1, max=8))
def _get(client: httpx.Client, url: str) -> dict[str, Any]:
    resp = client.get(url, timeout=30.0)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise TypeError("Expected JSON object")
    return data


def fetch_hf_benchmark_hints(
    *,
    model_name_to_id: dict[str, str],
    client: httpx.Client | None = None,
) -> list[BenchmarkSeed]:
    """Map a few HF rows onto known model_ids when names loosely match."""
    owned = client is None
    client = client or httpx.Client(headers={"User-Agent": "ai-price-intelligence/0.1"})
    retrieved = datetime.now(tz=UTC).replace(tzinfo=None)
    out: list[BenchmarkSeed] = []
    try:
        payload = _get(client, HF_DATASET_URL)
    except Exception as exc:  # noqa: BLE001
        logger.warning("HF leaderboard skip: %s", exc)
        return []
    finally:
        if owned:
            client.close()

    for row in payload.get("rows", []):
        row_data = row.get("row", {})
        name = str(row_data.get("fullname") or row_data.get("model") or "").lower()
        for key, model_id in model_name_to_id.items():
            if key.lower() in name:
                score = row_data.get("average") or row_data.get("MMLU") or row_data.get("score")
                if score is None:
                    continue
                try:
                    out.append(
                        BenchmarkSeed(
                            model_id=model_id,
                            benchmark_name="OpenLLM-Average",
                            score=float(score),
                            score_type=ScoreType.PCT,
                            eval_date=None,
                            source_url=SOURCE_URL,  # type: ignore[arg-type]
                            retrieved_at=retrieved,
                        )
                    )
                except Exception:  # noqa: BLE001
                    continue
                break
    logger.info("HF enrichment: %d rows mapped", len(out))
    return out
