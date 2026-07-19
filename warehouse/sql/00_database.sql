-- AI Price Intelligence warehouse bootstrap
-- Idempotent: safe to re-run.

CREATE DATABASE IF NOT EXISTS AI_PRICE_INTEL
  COMMENT = 'AI Model & Compute Price Intelligence — Marketplace dataset';

CREATE SCHEMA IF NOT EXISTS AI_PRICE_INTEL.RAW
  COMMENT = 'Landing zone for ingestion loads';

CREATE SCHEMA IF NOT EXISTS AI_PRICE_INTEL.CURATED
  COMMENT = 'SCD2 star-ish curated model';

CREATE SCHEMA IF NOT EXISTS AI_PRICE_INTEL.SHARE
  COMMENT = 'Secure views exposed via Marketplace share';
