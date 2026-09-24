"""Punto de entrada: `crear_app()` monta los routers de cada feature.

uv run python -m app                                   # recomendado: local y un worker
uv run uvicorn app.main:app --reload --port 8000       # desarrollo
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.commons import salud
from app.commons.config import Config, cargar_config
from app.commons.db import BaseDatos, ruta_db
from app.commons.db.cerrojo import CerrojoInstancia
from app.commons.db.migrar import aplicar_migraciones
from app.commons.errores import registrar_errores
from app.commons.llm import ClienteAnthropic, ClienteModelo
from app.commons.llm.llamar import LlamadorModelo
from app.commons.llm.pool import PoolEnVuelo
from app.commons.observabilidad import Trazador, TrazadorLangfuse
from app.commons.recursos import Recursos
from app.novel import router as novel
from app.process import cola
from app.process import router as generacion

TITULO = "storyMaker — API del backend v1"
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


def crear_app(
    config: Config | None = None,
    *,
    cliente_modelo: ClienteModelo | None = None,
    trazador: Trazador | None = None,
) -> FastAPI:
    """Crea la aplicación.

    Sin `config`, la lee de `config/` al arrancar, y si no vale el arranque falla en voz alta
    (RNF-15). `cliente_modelo` y `trazador` existen para que las pruebas inyecten sus dobles;
    en producción se usan las implementaciones de `commons/`.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        cfg = config if config is not None else cargar_config()
        ruta = ruta_db()
        cerrojo = CerrojoInstancia(ruta)
        cerrojo.adquirir()
        try:
            db = BaseDatos(ruta)
            db.ejecutar_sync(aplicar_migraciones)
            traz = trazador if trazador is not None else TrazadorLangfuse()
            pool = PoolEnVuelo(cfg.umbrales.en_vuelo.total)
            cliente = cliente_modelo if cliente_modelo is not None else ClienteAnthropic(cfg)
            recursos = Recursos(
                config=cfg,
                db=db,
                pool=pool,
                trazador=traz,
                llamador=LlamadorModelo(cfg, cliente, pool, traz),
            )
            recursos.contar_cola = lambda: cola.trabajos_en_cola(recursos)
            app.state.recursos = recursos
            try:
                yield
            finally:
                traz.cerrar()
        finally:
            cerrojo.liberar()

    app = FastAPI(
        title=TITULO,
        version=salud.VERSION_API,
        servers=SERVIDORES,
        openapi_tags=ETIQUETAS,
        lifespan=lifespan,
    )
    app.include_router(salud.router)
    app.include_router(novel.router)
    app.include_router(generacion.router)
    registrar_errores(app)
    return app


app = crear_app()
