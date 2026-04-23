.PHONY: install lint format test clean up down logs migrate

install:
	pip install -e ./shared[dev]
	pip install -e ./xui_client[dev]
	pip install -e ./backend[dev]
	pip install -e ./bot[dev]

lint:
	ruff check .
	$(MAKE) -s mypy

# Each module has its own mypy config in its pyproject.toml (strict + shared path).
# Running one module at a time avoids duplicate-module errors from `conftest.py`
# files that live under identical "tests" module paths across packages.
mypy:
	cd shared      && mypy shared     --strict
	cd xui_client  && mypy xui_client --strict
	cd backend     && mypy backend
	cd bot         && mypy bot        --strict

format:
	ruff format .
	ruff check --fix .

test:
	pytest shared xui_client backend bot -v

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	cd backend && alembic upgrade head

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
