PY ?= python
VENV ?= .venv
BIN := $(VENV)/bin

.PHONY: install demo test lint typecheck inventory verify clean

install:
	$(PY) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e ".[dev]"

demo:
	$(BIN)/python -m novela demo

test:
	$(BIN)/pytest -q

lint:
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

typecheck:
	$(BIN)/mypy src/

inventory:
	$(BIN)/python scripts/check_inventory.py

verify:
	$(BIN)/python scripts/check_inventory.py
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .
	$(BIN)/mypy src/
	$(BIN)/pytest -q
	$(BIN)/python -m novela demo
	test -f out/demo/manuscrito.md
	$(BIN)/python scripts/assert_demo_output.py

clean:
	rm -rf out/* .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	touch out/.gitkeep
