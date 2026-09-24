"""Servicio de calidad: los validadores del hook de capítulo y del rol editor.

El hook de capítulo corre solo validadores programáticos: no llama al modelo y por eso va
fuera del pool en vuelo (`architecture.md` § Paralelo y serie).
"""

from __future__ import annotations

import sqlite3

from pydantic import BaseModel, ConfigDict

from app.commons.config import Config
from app.commons.tiempo import ahora
from app.quality import repository
from app.quality.models import Defecto, InformeCritica, ResultadoValidador, Score
from app.quality.registro import comprobar
from app.quality.validadores.basicos import longitud, nombres_exactos

__all__ = [
    "Defecto",
    "EntradaHookCapitulo",
    "InformeCritica",
    "ResultadoValidador",
    "Score",
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


def hook_capitulo(config: Config, entrada: EntradaHookCapitulo) -> list[ResultadoValidador]:
    return [
        longitud(config, entrada.texto),
        nombres_exactos(entrada.texto, entrada.nombres),
    ]


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
