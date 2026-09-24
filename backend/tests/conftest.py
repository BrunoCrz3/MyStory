"""Fixtures comunes. Los dobles viven en `tests/dobles/`, nunca en `app/`."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import httpx
import jsonschema
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import crear_app
from tests.contrato.normalizar import cargar_contrato, schema_de_respuesta

_CONTRATO = cargar_contrato()


@pytest.fixture
def app() -> FastAPI:
    return crear_app()


@pytest.fixture
def cliente(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


ValidarContrato = Callable[[httpx.Response, str], None]


@pytest.fixture
def validar_contra_contrato() -> ValidarContrato:
    """Valida código, medio y cuerpo de una respuesta contra el schema aprobado."""

    def validar(respuesta: httpx.Response, op_id: str) -> None:
        medio = respuesta.headers.get("content-type", "").split(";")[0].strip()
        schema = schema_de_respuesta(_CONTRATO, op_id, respuesta.status_code, medio)
        if schema is None or medio not in ("application/json", "application/problem+json"):
            return
        cuerpo: Any = respuesta.json()
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(
            cuerpo
        )

    return validar
