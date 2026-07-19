"""Pydantic schemas for every ingested entity."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class ProviderType(StrEnum):
    LLM_API = "llm_api"
    CLOUD = "cloud"
    DATA_PLATFORM = "data_platform"


class Modality(StrEnum):
    TEXT = "text"
    EMBEDDING = "embedding"
    MULTIMODAL = "multimodal"
    CODE = "code"
    IMAGE = "image"


class LicenseType(StrEnum):
    PROPRIETARY = "proprietary"
    OPEN_WEIGHTS = "open_weights"


class ScoreType(StrEnum):
    PCT = "pct"
    ELO = "elo"
    PASS_AT_1 = "pass@1"
    OTHER = "other"


class PriceUnit(StrEnum):
    PER_1M_TOKENS = "per_1m_tokens"
    PER_1K_TOKENS = "per_1k_tokens"
    PER_TOKEN = "per_token"
    USD_PER_GPU_HOUR = "usd_per_gpu_hour"
    USD_PER_INSTANCE_HOUR = "usd_per_instance_hour"
    CREDITS_PER_1M_TOKENS = "credits_per_1m_tokens"


class Provider(BaseModel):
    provider_id: str = Field(min_length=1)
    name: str
    type: ProviderType
    website: HttpUrl | None = None


class ModelRecord(BaseModel):
    model_id: str
    provider_id: str
    model_name: str
    family: str | None = None
    modality: Modality = Modality.TEXT
    context_window_tokens: int | None = Field(default=None, ge=0)
    max_output_tokens: int | None = Field(default=None, ge=0)
    supports_tools: bool = False
    supports_vision: bool = False
    license: LicenseType = LicenseType.PROPRIETARY
    release_date: date | None = None
    deprecation_date: date | None = None
    is_active: bool = True


class ModelPriceSeed(BaseModel):
    model_id: str
    # Raw seed may use alternate units; normalize.py converts to per-1M USD.
    unit: PriceUnit = PriceUnit.PER_1M_TOKENS
    price_input: float = Field(ge=0)
    price_output: float = Field(ge=0)
    price_cached_input: float | None = Field(default=None, ge=0)
    batch_discount_pct: float | None = Field(default=None, ge=0, le=100)
    tier_notes: str | None = None
    source_url: HttpUrl
    retrieved_at: datetime | None = None
    currency: Literal["USD"] = "USD"

    @field_validator("unit")
    @classmethod
    def reject_unknown_units(cls, v: PriceUnit) -> PriceUnit:
        allowed = {
            PriceUnit.PER_1M_TOKENS,
            PriceUnit.PER_1K_TOKENS,
            PriceUnit.PER_TOKEN,
        }
        if v not in allowed:
            raise ValueError(f"Unsupported LLM price unit: {v}")
        return v


class BenchmarkSeed(BaseModel):
    model_id: str
    benchmark_name: str
    score: float
    score_type: ScoreType
    eval_date: date | None = None
    source_url: HttpUrl
    retrieved_at: datetime | None = None

    @model_validator(mode="after")
    def score_non_negative(self) -> BenchmarkSeed:
        if self.score < 0:
            raise ValueError("benchmark score must be non-negative")
        return self


class CortexPriceSeed(BaseModel):
    function_name: str
    model_name: str
    credits_per_1m_tokens: float = Field(ge=0)
    source_url: HttpUrl
    retrieved_at: datetime | None = None


class GpuInstance(BaseModel):
    instance_id: str
    cloud: Literal["aws", "azure", "gcp"]
    instance_name: str
    gpu_model: str
    gpu_count: int = Field(ge=1)
    vram_gb: float | None = Field(default=None, ge=0)
    region_scope: str | None = None


class GpuPrice(BaseModel):
    instance_id: str
    region: str
    price_on_demand_usd_hr: float | None = Field(default=None, ge=0)
    price_spot_usd_hr: float | None = Field(default=None, ge=0)
    price_1yr_reserved_usd_hr: float | None = Field(default=None, ge=0)
    source_url: HttpUrl | str
    retrieved_at: datetime
    # If True, on-demand/spot/reserved are per instance-hour and must be / gpu_count.
    prices_are_instance_hour: bool = True


class NormalizedModelPrice(BaseModel):
    model_id: str
    price_input_usd_per_1m_tokens: float
    price_output_usd_per_1m_tokens: float
    price_cached_input_usd_per_1m_tokens: float | None = None
    batch_discount_pct: float | None = None
    tier_notes: str | None = None
    source_url: str
    retrieved_at: datetime


class NormalizedGpuPrice(BaseModel):
    instance_id: str
    region: str
    price_on_demand_usd_hr: float | None
    price_spot_usd_hr: float | None
    price_1yr_reserved_usd_hr: float | None
    source_url: str
    retrieved_at: datetime


class SeedBundle(BaseModel):
    providers: list[Provider]
    models: list[ModelRecord]
    model_prices: list[ModelPriceSeed]
    benchmarks: list[BenchmarkSeed]
    cortex_prices: list[CortexPriceSeed]
    gpu_instances: list[GpuInstance] = Field(default_factory=list)
    gpu_prices: list[GpuPrice] = Field(default_factory=list)
