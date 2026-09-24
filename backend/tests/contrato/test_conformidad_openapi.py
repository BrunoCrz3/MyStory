"""Conformidad entre el OpenAPI que genera FastAPI y `specs/openapi.yaml`.

El contrato es la fuente: si divergen, falla este test y **se corrige el código**, nunca el
fichero aprobado (`specs/plan1.md` § 1).
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI

from tests.contrato.normalizar import cabecera, cargar_contrato, comparar, operaciones
from tests.contrato.pendientes import PENDIENTES


def test_conformidad_estructural(app: FastAPI) -> None:
    problemas = comparar(cargar_contrato(), app.openapi(), PENDIENTES)
    assert problemas == [], "El OpenAPI generado diverge del contrato:\n" + "\n".join(problemas)


def test_info_y_servers_coinciden(app: FastAPI) -> None:
    assert cabecera(app.openapi()) == cabecera(cargar_contrato())


def test_el_contrato_es_consistente_consigo_mismo() -> None:
    contrato = cargar_contrato()
    ops = operaciones(contrato)
    assert len(ops) == 20
    assert comparar(contrato, copy.deepcopy(contrato), frozenset()) == []


def _quitar_required(doc: dict[str, Any]) -> None:
    doc["components"]["schemas"]["BriefNovela"]["required"].remove("tono")


def _anadir_codigo(doc: dict[str, Any]) -> None:
    doc["paths"]["/salud"]["get"]["responses"]["503"] = {"description": "caído"}


def _cambiar_enum(doc: dict[str, Any]) -> None:
    doc["components"]["schemas"]["EstadoNovela"]["enum"].append("Archivada")


def _cambiar_operation_id(doc: dict[str, Any]) -> None:
    doc["paths"]["/novelas"]["get"]["operationId"] = "listarNovelasV2"


def _cambiar_parametro(doc: dict[str, Any]) -> None:
    doc["components"]["parameters"]["Limite"]["schema"]["maximum"] = 500


def _cambiar_medio(doc: dict[str, Any]) -> None:
    respuesta = doc["components"]["responses"]["NovelaNoEncontrada"]
    respuesta["content"]["application/json"] = respuesta["content"].pop("application/problem+json")


def _cambiar_nulabilidad(doc: dict[str, Any]) -> None:
    doc["components"]["schemas"]["Generacion"]["properties"]["checkpoint"]["type"] = "integer"


def _cambiar_cuerpo(doc: dict[str, Any]) -> None:
    cuerpo = doc["paths"]["/briefs/validacion"]["post"]["requestBody"]
    cuerpo["content"]["application/json"]["schema"] = {"$ref": "#/components/schemas/BriefNovela"}


MUTACIONES: list[Callable[[dict[str, Any]], None]] = [
    _quitar_required,
    _anadir_codigo,
    _cambiar_enum,
    _cambiar_operation_id,
    _cambiar_parametro,
    _cambiar_medio,
    _cambiar_nulabilidad,
    _cambiar_cuerpo,
]


@pytest.mark.parametrize("mutar", MUTACIONES, ids=lambda f: f.__name__)
def test_meta_una_mutacion_hace_fallar_la_comparacion(
    mutar: Callable[[dict[str, Any]], None],
) -> None:
    """Sin esto, un normalizador demasiado generoso daría un test que no puede fallar."""
    contrato = cargar_contrato()
    mutado = copy.deepcopy(contrato)
    mutar(mutado)
    assert comparar(contrato, mutado, frozenset()) != []
