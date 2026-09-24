"""Errores RFC 9457 con catálogo cerrado y handler central (spec § 4.3, TO-032)."""

from __future__ import annotations

from typing import Any

import jsonschema
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.commons.errores import CATALOGO, ErrorDominio, problemas, registrar_errores
from app.main import crear_app
from tests.contrato.normalizar import _resolver, cargar_contrato

CONTRATO = cargar_contrato()
SCHEMA_PROBLEMA: dict[str, Any] = _resolver({"$ref": "#/components/schemas/Problema"}, CONTRATO)


class _Cuerpo(BaseModel):
    edad: int


def _app_de_prueba() -> FastAPI:
    app = crear_app()

    for clase in CATALOGO:

        def lanzar(clase: type[ErrorDominio] = clase) -> None:
            raise clase("ocurrencia de prueba", capitulo=3)

        app.add_api_route(f"/prueba/{clase.slug}", lanzar, methods=["GET"])

    @app.post("/prueba/cuerpo")
    def cuerpo(c: _Cuerpo) -> dict[str, int]:
        return {"edad": c.edad}

    @app.get("/prueba/fallo")
    def fallo() -> None:
        raise RuntimeError("secreto interno que no debe salir")

    registrar_errores(app)
    return app


@pytest.fixture
def cliente_prueba() -> TestClient:
    return TestClient(_app_de_prueba(), raise_server_exceptions=False)


@pytest.mark.parametrize("clase", CATALOGO, ids=lambda c: c.slug)
def test_cada_error_produce_su_problema(
    cliente_prueba: TestClient, clase: type[ErrorDominio]
) -> None:
    r = cliente_prueba.get(f"/prueba/{clase.slug}")
    assert r.status_code == clase.status
    assert r.headers["content-type"].startswith("application/problem+json")
    cuerpo = r.json()
    assert cuerpo["type"] == f"/problemas/{clase.slug}"
    assert cuerpo["status"] == clase.status
    assert cuerpo["capitulo"] == 3
    jsonschema.validate(cuerpo, SCHEMA_PROBLEMA)


def test_cuerpo_invalido_da_422_peticion_invalida(cliente_prueba: TestClient) -> None:
    r = cliente_prueba.post("/prueba/cuerpo", json={"edad": "siete"})
    assert r.status_code == 422
    assert r.headers["content-type"].startswith("application/problem+json")
    cuerpo = r.json()
    assert cuerpo["type"] == "/problemas/peticion-invalida"
    assert "edad" in cuerpo["detail"]
    jsonschema.validate(cuerpo, SCHEMA_PROBLEMA)


def test_fallo_no_previsto_da_500_sin_detalles(cliente_prueba: TestClient) -> None:
    r = cliente_prueba.get("/prueba/fallo")
    assert r.status_code == 500
    cuerpo = r.json()
    assert cuerpo["type"] == "/problemas/error-interno"
    assert "secreto" not in r.text
    assert "Traceback" not in r.text
    jsonschema.validate(cuerpo, SCHEMA_PROBLEMA)


def test_el_catalogo_es_el_del_contrato() -> None:
    enum = set(CONTRATO["components"]["schemas"]["Problema"]["properties"]["type"]["enum"])
    assert {f"/problemas/{c.slug}" for c in CATALOGO} == enum


def test_el_openapi_usa_problema_y_no_el_422_de_fastapi() -> None:
    app = crear_app()

    @app.get("/prueba/{n}", responses=problemas(404))
    def ruta(n: int) -> dict[str, int]:
        return {"n": n}

    registrar_errores(app)
    doc = app.openapi()
    respuestas = doc["paths"]["/prueba/{n}"]["get"]["responses"]
    assert "422" not in respuestas
    assert "application/problem+json" in respuestas["404"]["content"]
    assert "Problema" in doc["components"]["schemas"]
    assert "HTTPValidationError" not in doc["components"]["schemas"]


def test_el_schema_problema_generado_es_el_del_contrato() -> None:
    from tests.contrato.normalizar import _normalizar_schema

    doc = crear_app().openapi()
    generado = _normalizar_schema(_resolver({"$ref": "#/components/schemas/Problema"}, doc))
    assert generado == _normalizar_schema(SCHEMA_PROBLEMA)
