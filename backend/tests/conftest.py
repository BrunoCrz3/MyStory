"""Fixtures comunes. Los dobles viven en `tests/dobles/`, nunca en `app/`."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx2
import jsonschema
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import crear_app
from tests.contrato.normalizar import cargar_contrato, schema_de_respuesta

_CONTRATO = cargar_contrato()

# Variables que conectarían la suite con servicios reales. Se vacían en toda prueba: la
# suite normal no llama al modelo ni a Langfuse (plan § 4.1).
_VARIABLES_REALES = (
    "ANTHROPIC_API_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_HOST",
    "PLAYWRIGHT_MCP_URL",
    "STORYMAKER_LECTURA_URL",
    "STORYMAKER_CONFIG_DIR",
)


@pytest.fixture(autouse=True)
def entorno_aislado(
    request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cada prueba con su base temporal y sin credenciales, salvo las marcadas `real`."""
    if request.node.get_closest_marker("real"):
        return
    for variable in _VARIABLES_REALES:
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("STORYMAKER_DB_PATH", str(tmp_path / "storymaker.db"))


@pytest.fixture
def app() -> FastAPI:
    return crear_app()


@pytest.fixture
def cliente(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


ValidarContrato = Callable[[httpx2.Response, str], None]


@pytest.fixture
def validar_contra_contrato() -> ValidarContrato:
    """Valida código, medio y cuerpo de una respuesta contra el schema aprobado."""

    def validar(respuesta: httpx2.Response, op_id: str) -> None:
        medio = respuesta.headers.get("content-type", "").split(";")[0].strip()
        schema = schema_de_respuesta(_CONTRATO, op_id, respuesta.status_code, medio)
        if schema is None or medio not in ("application/json", "application/problem+json"):
            return
        cuerpo: Any = respuesta.json()
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(
            cuerpo
        )

    return validar
