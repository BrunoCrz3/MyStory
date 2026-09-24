"""Servicio de calidad: los validadores del hook de capítulo y del rol editor.

El hook de capítulo corre solo validadores programáticos: no llama al modelo y por eso va
fuera del pool en vuelo (`architecture.md` § Paralelo y serie).
"""

from __future__ import annotations

import sqlite3

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

__all__ = [
    "Defecto",
    "EntidadPrevista",
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
    hechos: list[str] = Field(default_factory=list)
    reglas_mundo: list[str] = Field(default_factory=list)
    alcance: list[dict[str, str]] = Field(default_factory=list)
    previstas: list[EntidadPrevista] = Field(default_factory=list)


def hook_capitulo(config: Config, entrada: EntradaHookCapitulo) -> list[ResultadoValidador]:
    texto = entrada.texto
    return [
        longitud(config, texto),
        nombres_exactos(texto, entrada.nombres),
        consistencia_factica(config, texto, hechos=entrada.hechos, nombres=entrada.nombres),
        cumplimiento_brief(config, texto, alcance=entrada.alcance, previstas=entrada.previstas),
        reglas_mundo(texto, reglas=entrada.reglas_mundo),
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
