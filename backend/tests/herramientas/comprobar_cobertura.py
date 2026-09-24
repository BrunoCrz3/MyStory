"""Compara la cobertura medida con `validadores.cobertura_tests_minima` de `config/`.

    uv run pytest --cov=app --cov-report=json:../data/cobertura.json
    uv run python tests/herramientas/comprobar_cobertura.py

La cifra no se escribe aquí ni en `pyproject.toml`: se lee de la fuente única (RNF-14).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ_BACKEND))

from app.commons.config import cargar_config  # noqa: E402


def main() -> int:
    informe = RAIZ_BACKEND.parent / "data" / "cobertura.json"
    if not informe.exists():
        print(f"no existe {informe}: ejecuta antes pytest con --cov-report=json:{informe}")
        return 2
    medida = json.loads(informe.read_text(encoding="utf-8"))["totals"]["percent_covered"] / 100
    minima = cargar_config().umbrales.validadores.cobertura_tests_minima
    print(f"cobertura {medida:.1%} · mínima {minima:.0%}")
    return 0 if medida >= minima else 1


if __name__ == "__main__":
    sys.exit(main())
