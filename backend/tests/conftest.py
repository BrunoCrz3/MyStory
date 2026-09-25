"""Fixtures comunes. Los dobles viven en `tests/dobles/`, nunca en `app/`."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx2
import jsonschema
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hypothesis import settings

from app.commons.config import Config, cargar_config
from app.commons.db import BaseDatos
from app.commons.db.migrar import aplicar_migraciones
from app.commons.llm.llamar import LlamadorModelo
from app.commons.llm.pool import PoolEnVuelo
from app.commons.recursos import Recursos
from app.main import crear_app
from app.process.orquestador import Orquestador
from app.versioning.service import Publicacion
from tests.contrato.normalizar import cargar_contrato, schema_de_respuesta
from tests.dobles.guiones import guion_revision
from tests.dobles.modelo import ModeloGuionizado
from tests.dobles.render import RenderGuionizado
from tests.dobles.trazador import RegistroTrazas
from tests.fixtures.lectura.servidor import paginas  # noqa: F401  (fixture compartida)

_CONTRATO = cargar_contrato()

# Sin límite de tiempo por ejemplo: una propiedad no puede fallar por lo rápida que sea la
# máquina que la ejecuta.
settings.register_profile("storymaker", deadline=None)
settings.load_profile("storymaker")

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
    # Sin credenciales a propósito: el `.env` de la raíz no tiene que haber llegado (TO-054).
    monkeypatch.setenv("STORYMAKER_SIN_ENV", "1")


@pytest.fixture
def app() -> FastAPI:
    return crear_app()


@pytest.fixture
def cliente(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@dataclass
class Instancia:
    """App arrancada con los dos dobles, para afirmar sobre lo que ha hecho."""

    cliente: TestClient
    modelo: ModeloGuionizado
    trazas: RegistroTrazas
    app: FastAPI
    render: RenderGuionizado


@pytest.fixture
def instancia() -> Iterator[Instancia]:
    config = cargar_config()
    modelo = ModeloGuionizado(config)
    guion_revision(modelo)
    trazas = RegistroTrazas()
    render = RenderGuionizado()
    app = crear_app(config, cliente_modelo=modelo, trazador=trazas, render_visual=render)
    with TestClient(app) as c:
        yield Instancia(cliente=c, modelo=modelo, trazas=trazas, app=app, render=render)


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


@dataclass
class Entorno:
    """Los recursos de una instancia con los dos dobles, sin HTTP: para probar servicios."""

    recursos: Recursos
    modelo: ModeloGuionizado
    trazas: RegistroTrazas
    render: RenderGuionizado = field(default_factory=RenderGuionizado)

    async def crear_novela(self, brief: dict[str, Any]) -> str:
        from app.intake.service import BriefNovela
        from app.novel.service import crear_novela

        novela = await crear_novela(
            self.recursos.db, self.recursos.config, BriefNovela.model_validate(brief)
        )
        return str(novela.novel_id)

    def orquestador(self) -> Orquestador:
        """El orquestador de producción, con la publicación de `versioning/`."""
        return Orquestador(self.recursos, Publicacion(self.recursos.config, self.render))

    def consultar(self, sql: str, *parametros: Any) -> list[sqlite3.Row]:
        return self.recursos.db.ejecutar_sync(lambda con: con.execute(sql, parametros).fetchall())


def _sin_lean_incremental(config: Config) -> Config:
    formal = config.umbrales.formal.model_copy(update={"lean_incremental": False})
    return config.model_copy(
        update={"umbrales": config.umbrales.model_copy(update={"formal": formal})}
    )


@pytest.fixture
def entorno(tmp_path: Path) -> Entorno:
    return crear_entorno(tmp_path / "entorno.db")


def crear_entorno(ruta: Path) -> Entorno:
    """Recursos con los dos dobles sobre la base de `ruta`, migrada.

    El chequeo incremental de Lean se apaga aquí (A-06 del plan 4): lanzaría `lake build` en
    cada capítulo aceptado de cada prueba de servicio y triplica la suite. Lo prueban
    `tests/process/test_lean_incremental.py`, que lo enciende, y las pruebas por HTTP de
    `instancia`, que usan la configuración real sin tocar."""
    config = _sin_lean_incremental(cargar_config())
    db = BaseDatos(ruta)
    db.ejecutar_sync(aplicar_migraciones)
    modelo = ModeloGuionizado(config)
    guion_revision(modelo)
    trazas = RegistroTrazas()
    pool = PoolEnVuelo(config.umbrales.en_vuelo.total)
    recursos = Recursos(
        config=config,
        db=db,
        pool=pool,
        trazador=trazas,
        llamador=LlamadorModelo(config, modelo, pool, trazas),
    )
    return Entorno(recursos=recursos, modelo=modelo, trazas=trazas)
