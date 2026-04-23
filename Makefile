.PHONY: install lint format test clean

install:
	pip install -e ./shared
	pip install -e ./xui_client
	pip install -e ./backend[dev]
	pip install -e ./bot[dev]

lint:
	ruff check .
	mypy shared xui_client backend bot

format:
	ruff format .
	ruff check --fix .

test:
	pytest shared xui_client backend bot -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
