PYTHON := uv run
UV_CACHE_DIR ?= /tmp/uv-cache
WEB_DIR := web

.PHONY: backend frontend tests lint format frontend-tests frontend-lint frontend-typecheck frontend-build frontend-check pre-commit
.PHONY: migrate

backend:
	VK_ARCHIVE_CONFIG=$(CURDIR)/config.toml UV_CACHE_DIR=$(UV_CACHE_DIR) $(PYTHON) --directory backend python -m app.main

tests:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(PYTHON) --directory backend pytest

migrate:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(PYTHON) --directory backend alembic -c ../alembic.ini upgrade head

lint:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(PYTHON) --directory backend ruff check app tests

format:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(PYTHON) --directory backend ruff format app tests

frontend:
	npm --prefix $(WEB_DIR) run dev

frontend-tests:
	npm --prefix $(WEB_DIR) run test -- --run

frontend-lint:
	npm --prefix $(WEB_DIR) run lint

frontend-typecheck:
	npm --prefix $(WEB_DIR) run typecheck

frontend-build:
	npm --prefix $(WEB_DIR) run build

frontend-check: frontend-lint frontend-typecheck frontend-tests

pre-commit:
	./backend/.venv/bin/pre-commit run --all-files
