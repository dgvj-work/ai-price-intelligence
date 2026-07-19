.PHONY: setup test lint typecheck dry-run deploy-warehouse refresh deploy-app ci

PYTHON ?= python3.11
VENV ?= .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python

setup:
	@if command -v uv >/dev/null 2>&1; then \
		uv venv $(VENV) --python 3.11; \
		uv pip install -e ".[dev,app]" --python $(PY); \
	else \
		$(PYTHON) -m venv $(VENV); \
		$(PIP) install -U pip; \
		$(PIP) install -e ".[dev,app]"; \
	fi

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check ingestion warehouse tests
	$(PY) -m ruff format --check ingestion warehouse tests

typecheck:
	$(PY) -m mypy ingestion

ci: lint typecheck test

dry-run:
	$(PY) -m ingestion.run_refresh --dry-run --skip-cloud --skip-hf

deploy-warehouse:
	$(PY) warehouse/deploy.py

refresh:
	$(PY) -m ingestion.run_refresh

deploy-app:
	cd native_app && snow app run
