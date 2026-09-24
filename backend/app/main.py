"""Punto de entrada: `crear_app()` monta los routers de cada feature."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.commons.config import Config, cargar_config
from app.commons.db import BaseDatos, ruta_db
from app.commons.db.migrar import aplicar_migraciones
from app.commons.errores import registrar_errores

TITULO = "storyMaker — API del backend v1"
VERSION_API = "1.1.0"
SERVIDORES = [{"url": "http://127.0.0.1:8000", "description": "Instancia local."}]
ETIQUETAS = [
    {"name": "novelas"},
    {"name": "intake"},
    {"name": "generacion"},
    {"name": "lectura"},
    {"name": "canon"},
    {"name": "regeneracion"},
    {"name": "export"},
    {"name": "meta"},
]


def crear_app(config: Config | None = None) -> FastAPI:
    """Crea la aplicación. Sin `config`, la lee de `config/` al arrancar, y si no vale el
    arranque falla en voz alta (RNF-15)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.config = config if config is not None else cargar_config()
        db = BaseDatos(ruta_db())
        db.ejecutar_sync(aplicar_migraciones)
        app.state.db = db
        yield

    app = FastAPI(
        title=TITULO,
        version=VERSION_API,
        servers=SERVIDORES,
        openapi_tags=ETIQUETAS,
        lifespan=lifespan,
    )
    registrar_errores(app)
    return app


app = crear_app()
