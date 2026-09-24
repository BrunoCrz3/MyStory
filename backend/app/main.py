"""Punto de entrada: `crear_app()` monta los routers de cada feature."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

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


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


def crear_app() -> FastAPI:
    return FastAPI(
        title=TITULO,
        version=VERSION_API,
        servers=SERVIDORES,
        openapi_tags=ETIQUETAS,
        lifespan=_lifespan,
    )


app = crear_app()
