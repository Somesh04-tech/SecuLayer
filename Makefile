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
	@echo "Classifier download (seculayer fetch-model) arrives in M2; recorded scores are used until then."

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

eval:
	@echo "make eval: not implemented yet (M7)"; exit 1

eval-live:
	@echo "make eval-live: not implemented yet (M7)"; exit 1

record:
	@echo "make record: not implemented yet (M3)"; exit 1

replay-check:
	@echo "make replay-check: not implemented yet (M6)"; exit 1

types:
	@echo "make types: not implemented yet (M3)"; exit 1
