PYTHON := uv run
WEB_DIR := web
DEMO_DATA_ARGS ?= --reset
UV_ENV := $(if $(UV_CACHE_DIR),UV_CACHE_DIR=$(UV_CACHE_DIR),)

.PHONY: backend frontend test tests lint format frontend-test frontend-test-coverage frontend-lint frontend-typecheck frontend-build frontend-check pre-commit demo-data
.PHONY: migrate

backend:
	$(UV_ENV) $(PYTHON) --directory backend python -m app.main $(ARGS)

test:
	$(UV_ENV) $(PYTHON) --directory backend pytest

tests: test

migrate:
	$(UV_ENV) $(PYTHON) --directory backend alembic -c ../alembic.ini upgrade head

lint:
	$(UV_ENV) $(PYTHON) --directory backend ruff check app test

format:
	$(UV_ENV) $(PYTHON) --directory backend ruff format app test

frontend:
	npm --prefix $(WEB_DIR) run dev

frontend-test:
	npm --prefix $(WEB_DIR) run test -- --run

frontend-test-coverage:
	npm --prefix $(WEB_DIR) run test:coverage

frontend-lint:
	npm --prefix $(WEB_DIR) run lint

frontend-typecheck:
	npm --prefix $(WEB_DIR) run typecheck

frontend-build:
	npm --prefix $(WEB_DIR) run build

frontend-check: frontend-lint frontend-typecheck frontend-test

pre-commit:
	./backend/.venv/bin/pre-commit run --all-files

demo-data:
	$(UV_ENV) $(PYTHON) --directory backend python -m scripts.generate_demo_data $(DEMO_DATA_ARGS) $(ARGS)
