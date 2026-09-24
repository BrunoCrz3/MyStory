"""Servicio de la obra. Crea la novela con su brief, sin lanzar la generación
(RF-INTAKE-04), y la sirve (RF-NOVEL-02, RF-NOVEL-03)."""

from __future__ import annotations

import sqlite3
import uuid

from app.commons.config import Config
from app.commons.db import BaseDatos
from app.commons.errores import NovelaNoEncontrada
from app.commons.tiempo import ahora
from app.guardrail import service as guardrail
from app.intake import service as intake
from app.intake.service import BriefNovela
from app.novel import repository
from app.novel.models import (
    ESTADOS_TERMINALES_NOVELA,
    EstadoCapitulo,
    EstadoNovela,
    ReglaMundo,
)
from app.novel.schemas import ListaNovelas, Novela, NovelaResumen

__all__ = [
    "ESTADOS_TERMINALES_NOVELA",
    "EstadoCapitulo",
    "EstadoNovela",
    "ReglaMundo",
    "crear_capitulo",
    "crear_novela",
    "listar_novelas",
    "obtener_novela",
    "reglas_del_mundo",
]


def _version_vigente(con: sqlite3.Connection, *, novel_id: str) -> int | None:
    # Hasta que exista `version_novela` (P25) ninguna novela tiene versión publicada.
    existe = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'version_novela'"
    ).fetchone()
    if existe is None:
        return None
    fila = con.execute(
        "SELECT max(version) FROM version_novela WHERE novel_id = ?", (novel_id,)
    ).fetchone()
    valor: int | None = fila[0]
    return valor


def _novela(con: sqlite3.Connection, *, novel_id: str) -> Novela:
    obra = repository.leer_obra(con, novel_id=novel_id)
    brief = intake.leer_brief(con, novel_id=novel_id)
    if obra is None or brief is None:
        raise NovelaNoEncontrada(f"no existe la novela {novel_id}", novel_id=novel_id)
    return Novela(
        novel_id=obra["novel_id"],
        titulo=obra["titulo"],
        estado=obra["estado"],
        version_vigente=_version_vigente(con, novel_id=novel_id),
        total_capitulos=obra["total_capitulos"],
        creada_en=obra["creada_en"],
        brief=brief,
    )


async def crear_novela(db: BaseDatos, config: Config, brief: BriefNovela) -> Novela:
    novel_id = str(uuid.uuid4())
    momento = ahora()

    def escribir(con: sqlite3.Connection) -> Novela:
        repository.insertar_obra(
            con,
            novel_id=novel_id,
            brief=brief,
            total=config.umbrales.obra.capitulos,
            ahora=momento,
        )
        intake.registrar_brief(con, novel_id=novel_id, brief=brief, ahora=momento)
        guardrail.registrar_palabras_novela(
            con, novel_id=novel_id, palabras=brief.palabras_prohibidas
        )
        return _novela(con, novel_id=novel_id)

    return await db.en_transaccion(escribir)


async def obtener_novela(db: BaseDatos, novel_id: str) -> Novela:
    return await db.ejecutar(lambda con: _novela(con, novel_id=novel_id))


async def listar_novelas(db: BaseDatos, *, limite: int, desplazamiento: int) -> ListaNovelas:
    def leer(con: sqlite3.Connection) -> ListaNovelas:
        filas = repository.listar_obras(con, limite=limite, desplazamiento=desplazamiento)
        return ListaNovelas(
            items=[
                NovelaResumen(
                    novel_id=f["novel_id"],
                    titulo=f["titulo"],
                    estado=f["estado"],
                    version_vigente=_version_vigente(con, novel_id=f["novel_id"]),
                    creada_en=f["creada_en"],
                )
                for f in filas
            ],
            total=repository.contar_obras(con),
        )

    return await db.ejecutar(leer)


def reglas_del_mundo(con: sqlite3.Connection, *, novel_id: str) -> list[ReglaMundo]:
    return repository.leer_reglas(con, novel_id=novel_id)


def crear_capitulo(con: sqlite3.Connection, *, novel_id: str, numero: int, version: int) -> str:
    """Crea la fila del capítulo `numero` para la versión `version`, en `Pendiente` (D-05)."""
    return repository.insertar_capitulo(con, novel_id=novel_id, numero=numero, version=version)
