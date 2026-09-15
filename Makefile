# Envoltorio fino sobre `scripts/tasks.py`, que es donde vive la definicion de
# cada target. La logica no esta aqui para que Linux, macOS y Windows ejecuten
# exactamente los mismos pasos (DECISIONS.md, D-14).
#
# En Windows sin GNU make, el equivalente es `./make.ps1 <target>`.
PY ?= python
VENV ?= .venv

# `tasks.py` lee VENV del entorno; el interprete lo elige `PY`.
export VENV

TASKS := $(PY) scripts/tasks.py

.PHONY: install demo test lint typecheck inventory verify clean

install:
	$(TASKS) install

demo:
	$(TASKS) demo

test:
	$(TASKS) test

lint:
	$(TASKS) lint

typecheck:
	$(TASKS) typecheck

inventory:
	$(TASKS) inventory

verify:
	$(TASKS) verify

clean:
	$(TASKS) clean
