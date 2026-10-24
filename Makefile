# SecuLayer tasks. See docs/PLAN.md §8.4.
# Everything heavy stays on the external drive: the caches live in .cache/ (§8.5).

SHELL := /bin/bash
REPO := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
export UV_CACHE_DIR ?= $(REPO)/.cache/uv
export npm_config_cache ?= $(REPO)/.cache/npm
export PLAYWRIGHT_BROWSERS_PATH ?= $(REPO)/.cache/ms-playwright

WEB := $(REPO)/web

.PHONY: help setup check check-py check-web e2e build eval eval-live record replay-check dev types

help:
	@echo "make setup        first-time install (needs the network)"
	@echo "make check        lint, types and unit tests; no network"
	@echo "make e2e          build the frontend and run Playwright in replay mode"
	@echo "make dev          backend with reload on :8765 plus Vite on :5173"
	@echo "make eval | eval-live | record | replay-check | types"

setup:
	uv sync --frozen
	cd "$(WEB)" && npm ci
	cd "$(WEB)" && npx playwright install --only-shell chromium
	uv run --frozen seculayer fetch-model || echo "Classifier download failed; recorded scores will be used."

check: check-py check-web

check-py:
	uv run --frozen ruff check src tests
	uv run --frozen ruff format --check src tests
	uv run --frozen mypy src/seculayer
	uv run --frozen pytest -q -p no:cacheprovider

check-web:
	cd "$(WEB)" && npm run lint
	cd "$(WEB)" && npm run typecheck
	cd "$(WEB)" && npm test

build:
	cd "$(WEB)" && npm run build

e2e: build
	mkdir -p "$(REPO)/artifacts/screenshots"
	cd "$(WEB)" && npx playwright test

dev:
	@trap 'kill 0' EXIT INT TERM; \
	uv run --frozen seculayer serve --reload & \
	cd "$(WEB)" && npm run dev

# Recomputes every metric offline from the recordings (docs/PLAN.md §7.4).
eval:
	uv run --frozen seculayer eval --mode replay

# Records any missing calls (budgeted, asks first), then evaluates.
eval-live:
	uv run --frozen seculayer eval --mode live --record --configs A,B,C,D

# Fills in missing recordings (live calls, within SECULAYER_TOKEN_BUDGET). Override CASES,
# CONFIGS and TRIALS, e.g. make record CASES='inbox.*' CONFIGS=A,B TRIALS=3.
CASES ?= inbox.hidden_forward,support.override
CONFIGS ?= A,B
TRIALS ?= 3
record:
	uv run --frozen seculayer record --cases '$(CASES)' --configs '$(CONFIGS)' --trials $(TRIALS)

replay-check:
	uv run --frozen seculayer replay-check

types:
	uv run --frozen seculayer export-openapi web/src/api/openapi.json
	cd "$(WEB)" && npx openapi-typescript src/api/openapi.json -o src/api/types.gen.ts
