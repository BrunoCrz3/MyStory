"""`ejemplos/brief-ejemplo.json` es el `example` de `BriefNovela` del contrato, sin más."""

from __future__ import annotations

import json

from app.intake.service import BriefNovela
from tests.arquitectura.comprobadores import RAIZ_REPO
from tests.contrato.normalizar import cargar_contrato


def test_el_brief_de_ejemplo_es_el_example_del_contrato_y_valida() -> None:
    fichero = RAIZ_REPO / "ejemplos" / "brief-ejemplo.json"
    brief = json.loads(fichero.read_text(encoding="utf-8"))
    assert brief == cargar_contrato()["components"]["schemas"]["BriefNovela"]["example"]
    BriefNovela.model_validate(brief)
