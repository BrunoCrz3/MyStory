"""Arranque de la instancia.

Monta los routers de cada feature y
hace las tres cosas que tienen que pasar antes de servir la primera peticion:
leer los umbrales, comprobar que la fase declarada es coherente con ellos y
aplicar las migraciones pendientes.

**Escucha en `127.0.0.1` por defecto** (RNF-12, A-39). No es un servicio
compartido: sin autenticacion en v1, exponerlo en `0.0.0.0` abriria el canon
entero a la red.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from app.commons.config import Umbrales, cargar_umbrales, verificar_arranque
from app.commons.db import migraciones
from app.commons.db.conexion import crear_conexion
from app.commons.http import registrar_manejadores
from app.novel.router import router as router_de_novel

HOST_POR_DEFECTO = "127.0.0.1"


class Salud(BaseModel):
    """Estado de la instancia. La fase de medicion es consultable, no un silencio."""

    version_de_umbrales: int
    fase_de_medicion: bool
    ultima_migracion: int


@asynccontextmanager
async def ciclo_de_vida(aplicacion: FastAPI) -> AsyncIterator[None]:
    umbrales = cargar_umbrales()
    verificar_arranque(umbrales)

    conexion = crear_conexion()
    migraciones.aplicar_migraciones(conexion)

    aplicacion.state.umbrales = umbrales
    aplicacion.state.conexion = conexion
    try:
        yield
    finally:
        conexion.close()


app = FastAPI(
    title="MyStory",
    summary="Backend de produccion de una novela con canon consistente",
    lifespan=ciclo_de_vida,
)
registrar_manejadores(app)
app.include_router(router_de_novel)


@app.get("/salud")
async def salud() -> Salud:
    # Asincrono a proposito: la conexion se abre en el hilo del bucle de eventos
    # y SQLite solo la deja usar ahi. Un endpoint sincrono correria en el pool de
    # hilos y fallaria en voz alta, que es justo lo que queremos que pase.
    umbrales: Umbrales = app.state.umbrales
    aplicadas = migraciones.migraciones_aplicadas(app.state.conexion)
    return Salud(
        version_de_umbrales=umbrales.version,
        # `cerrar_el_paso` en false es la fase de medicion: se puntua y se
        # registra, y quien decide sigue siendo el autor (RF-PROC-07).
        fase_de_medicion=not umbrales.medicion.cerrar_el_paso,
        ultima_migracion=aplicadas[-1].numero if aplicadas else 0,
    )


def ejecutar() -> None:
    """Arranque directo. El puerto no tiene defecto propio a proposito: lo pone
    el comando de `AGENTS.md` (`--port`) o `uvicorn`, y asi no hay una cifra mas
    escrita suelta en el codigo (A-40)."""
    import uvicorn

    opciones: dict[str, object] = {"host": os.environ.get("MYSTORY_HOST", HOST_POR_DEFECTO)}
    puerto = os.environ.get("MYSTORY_PUERTO")
    if puerto:
        opciones["port"] = int(puerto)
    uvicorn.run(app, **opciones)  # type: ignore[arg-type]


if __name__ == "__main__":
    ejecutar()
