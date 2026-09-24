"""Servicio de calidad: los validadores del hook de capítulo y del rol editor.

El hook de capítulo corre solo validadores programáticos: no llama al modelo y por eso va
fuera del pool en vuelo (`architecture.md` § Paralelo y serie).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from functools import partial

import anyio
from pydantic import BaseModel, ConfigDict, Field

from app.commons.config import Config
from app.commons.tiempo import ahora
from app.quality import repository
from app.quality.models import Defecto, InformeCritica, ResultadoValidador, Score
from app.quality.registro import comprobar
from app.quality.validadores.basicos import longitud, nombres_exactos
from app.quality.validadores.canon import (
    EntidadPrevista,
    consistencia_factica,
    cumplimiento_brief,
    reglas_mundo,
)
from app.quality.validadores.texto import (
    Focalizacion,
    Persona,
    Tiempo,
    calidad_prosa,
    integridad_pov,
)

__all__ = [
    "Defecto",
    "EntidadPrevista",
    "EntradaHookCapitulo",
    "InformeCritica",
    "ResultadoValidador",
    "Score",
    "en_paralelo",
    "hook_capitulo",
    "informes_de_capitulo",
    "registrar_informe",
    "ultimo_informe",
]


class EntradaHookCapitulo(BaseModel):
    """Lo que el hook de capítulo necesita para validar un borrador."""

    model_config = ConfigDict(frozen=True)

    titulo: str
    texto: str
    nombres: list[str]
    hechos: list[str] = Field(default_factory=list)
    reglas_mundo: list[str] = Field(default_factory=list)
    alcance: list[dict[str, str]] = Field(default_factory=list)
    previstas: list[EntidadPrevista] = Field(default_factory=list)
    anteriores: list[str] = Field(default_factory=list)
    persona: Persona = "tercera"
    tiempo_verbal: Tiempo = "pasado"
    focalizacion: Focalizacion = "interna"
    pov: str = ""
    personajes: list[str] = Field(default_factory=list)


async def en_paralelo(
    tareas: list[Callable[[], ResultadoValidador]],
) -> list[ResultadoValidador]:
    """Corre las tareas a la vez, cada una en un hilo, y devuelve los resultados en su orden.

    Los validadores del hook son deterministas y no llaman al modelo: no piden hueco en el
    pool en vuelo ni esperan a nadie (`architecture.md` § Paralelo y serie).
    """
    resultados: dict[int, ResultadoValidador] = {}

    async def correr(i: int, tarea: Callable[[], ResultadoValidador]) -> None:
        resultados[i] = await anyio.to_thread.run_sync(tarea)

    async with anyio.create_task_group() as grupo:
        for i, tarea in enumerate(tareas):
            grupo.start_soon(correr, i, tarea)
    return [resultados[i] for i in range(len(tareas))]


async def hook_capitulo(config: Config, entrada: EntradaHookCapitulo) -> list[ResultadoValidador]:
    """Los siete validadores programáticos del hook de capítulo, en paralelo."""
    e, texto = entrada, entrada.texto
    return await en_paralelo(
        [
            partial(longitud, config, texto),
            partial(nombres_exactos, texto, e.nombres),
            partial(consistencia_factica, config, texto, hechos=e.hechos, nombres=e.nombres),
            partial(cumplimiento_brief, config, texto, alcance=e.alcance, previstas=e.previstas),
            partial(reglas_mundo, texto, reglas=e.reglas_mundo),
            partial(calidad_prosa, config, texto, anteriores=e.anteriores),
            partial(
                integridad_pov,
                config,
                texto,
                persona=e.persona,
                tiempo_verbal=e.tiempo_verbal,
                focalizacion=e.focalizacion,
                pov=e.pov,
                personajes=e.personajes,
            ),
        ]
    )


def registrar_informe(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    capitulo_id: str,
    intento: int,
    decision: str,
    resultados: list[ResultadoValidador],
) -> str:
    """Guarda el informe de crítica de un intento con sus defectos y un score por validador
    ejecutado. Corre en la transacción de quien decide, así que decisión e informe quedan
    juntos o no queda ninguno. Un validador que no corre donde dice el registro falla aquí."""
    for resultado in resultados:
        comprobar(resultado)
    return repository.insertar_informe(
        con,
        novel_id=novel_id,
        capitulo_id=capitulo_id,
        intento=intento,
        decision=decision,
        creado_en=ahora(),
        resultados=resultados,
    )


def informes_de_capitulo(
    con: sqlite3.Connection, *, novel_id: str, capitulo_id: str
) -> list[InformeCritica]:
    return repository.informes_de_capitulo(con, novel_id=novel_id, capitulo_id=capitulo_id)


def ultimo_informe(
    con: sqlite3.Connection, *, novel_id: str, capitulo_id: str
) -> InformeCritica | None:
    informes = informes_de_capitulo(con, novel_id=novel_id, capitulo_id=capitulo_id)
    return informes[-1] if informes else None
