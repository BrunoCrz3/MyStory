"""Versiones de la novela: gate de publicación, publicación inmutable y lectura por versión.

El gate corre sin modelo (`architecture.md` § Hooks y policy engine). En F1 ejecuta
`estructura_edicion` y `elementos_obligatorios`; las fases siguientes añaden los suyos (D-17).
Publicar escribe la versión y sus vínculos en la transacción de quien publica, y el hash del
contenido es lo que hace comprobable que después no cambia (RNF-07).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from functools import partial
from typing import Any

from app.commons.config import Config
from app.commons.db import BaseDatos
from app.commons.errores import NovelaNoEncontrada, VersionNoEncontrada
from app.commons.tiempo import ahora
from app.intake.service import leer_brief
from app.novel import service as novel
from app.process.service import VeredictoGate
from app.versioning import gate, repository
from app.versioning.schemas import Capitulo, CapituloIndice, Version, VersionResumen

__all__ = [
    "Capitulo",
    "Publicacion",
    "Version",
    "VersionResumen",
    "hash_de_version",
    "listar_capitulos",
    "listar_versiones",
    "obtener_capitulo",
    "obtener_version",
]


def _candidatos(con: sqlite3.Connection, *, novel_id: str, version: int) -> dict[int, str]:
    """Qué fila de capítulo leerá cada número en la versión que se va a publicar.

    Los aceptados de esta versión; para los que no se reescribieron, la fila que ya leía la
    versión anterior (D-05).
    """
    anteriores = (
        repository.vinculos(con, novel_id=novel_id, version=version - 1) if version > 1 else {}
    )
    nuevos = repository.aceptados_de_version(con, novel_id=novel_id, version=version)
    return {**anteriores, **{n: str(f["id"]) for n, f in nuevos.items()}}


def _hash(titulo: str | None, capitulos: list[dict[str, Any]]) -> str:
    """SHA-256 del contenido canónico: título de la obra y, en orden, número, título y texto."""
    canonico = {
        "titulo": titulo,
        "capitulos": [
            {"numero": c["numero"], "titulo": c["titulo"], "texto": c["texto"]}
            for c in sorted(capitulos, key=lambda c: int(c["numero"]))
        ],
    }
    datos = json.dumps(canonico, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(datos.encode("utf-8")).hexdigest()


def _contenido(con: sqlite3.Connection, *, novel_id: str, ids: list[str]) -> list[dict[str, Any]]:
    return list(repository.contenido_de_capitulos(con, novel_id=novel_id, ids=ids).values())


def hash_de_version(con: sqlite3.Connection, *, novel_id: str, version: int) -> str:
    """Recalcula el hash de una versión publicada desde lo que lee hoy."""
    fila = repository.leer_version(con, novel_id=novel_id, version=version)
    if fila is None:
        raise VersionNoEncontrada(
            f"la novela {novel_id} no tiene la versión {version}", novel_id=novel_id
        )
    ids = list(repository.vinculos(con, novel_id=novel_id, version=version).values())
    return _hash(fila["titulo"], _contenido(con, novel_id=novel_id, ids=ids))


class Publicacion:
    """Implementación del puerto `Publicador` de `process/`."""

    def __init__(self, config: Config) -> None:
        self.config = config

    def gate(self, con: sqlite3.Connection, *, novel_id: str, version: int) -> list[VeredictoGate]:
        ids = list(_candidatos(con, novel_id=novel_id, version=version).values())
        capitulos = _contenido(con, novel_id=novel_id, ids=ids)
        return [
            gate.estructura_edicion(con, novel_id=novel_id, capitulos=capitulos),
            gate.elementos_obligatorios(con, novel_id=novel_id, ids=ids),
            gate.cierre_arco(self.config, con, novel_id=novel_id, version=version, ids=ids),
        ]

    def publicar(
        self,
        con: sqlite3.Connection,
        *,
        novel_id: str,
        version: int,
        generacion_id: str,
        motivo: str | None,
    ) -> str:
        candidatos = _candidatos(con, novel_id=novel_id, version=version)
        anterior = (
            repository.leer_version(con, novel_id=novel_id, version=version - 1)
            if version > 1
            else None
        )
        previos = (
            repository.vinculos(con, novel_id=novel_id, version=version - 1) if anterior else {}
        )
        titulo = novel.titulo_de_obra(con, novel_id=novel_id)
        huella = _hash(titulo, _contenido(con, novel_id=novel_id, ids=list(candidatos.values())))
        repository.insertar_version(
            con,
            novel_id=novel_id,
            version=version,
            version_anterior_id=None if anterior is None else anterior["id"],
            titulo=titulo,
            hash_contenido=huella,
            motivo=motivo,
            generacion_id=generacion_id,
            ahora=ahora(),
        )
        for numero, capitulo_id in sorted(candidatos.items()):
            repository.insertar_vinculo(
                con,
                novel_id=novel_id,
                version=version,
                numero=numero,
                capitulo_id=capitulo_id,
                # D-05: un capítulo no reescrito es la misma fila; cambió si la fila es otra.
                modificado=anterior is not None and previos.get(numero) != capitulo_id,
            )
        return huella


# --- Lectura ---------------------------------------------------------------------------


def _exigir_novela(con: sqlite3.Connection, novel_id: str) -> None:
    if novel.estado_de_obra(con, novel_id=novel_id) is None:
        raise NovelaNoEncontrada(f"no existe la novela {novel_id}", novel_id=novel_id)


def _exigir_version(con: sqlite3.Connection, novel_id: str, version: int) -> dict[str, Any]:
    _exigir_novela(con, novel_id)
    fila = repository.leer_version(con, novel_id=novel_id, version=version)
    if fila is None:
        raise VersionNoEncontrada(
            f"la novela {novel_id} no tiene la versión {version} publicada", novel_id=novel_id
        )
    return fila


def _resumen(con: sqlite3.Connection, fila: dict[str, Any]) -> VersionResumen:
    return VersionResumen(
        version=fila["version"],
        publicada_en=fila["publicada_en"],
        version_anterior=fila["version_anterior"],
        capitulos_modificados=repository.modificados(
            con, novel_id=fila["novel_id"], version=fila["version"]
        ),
        motivo=fila["motivo"],
    )


def _capitulo(fila: dict[str, Any]) -> Capitulo:
    return Capitulo(
        numero=fila["numero"],
        titulo=fila["titulo"],
        estado=fila["estado"],
        texto=fila["texto"],
        palabras=fila["palabras"],
        resumen=fila["resumen"],
        gancho_cierre=fila["gancho_cierre"],
        pov=fila["pov"],
        lugar=fila["lugar"],
        funcion_dramatica=fila["funcion_dramatica"],
        intentos=fila["intentos"],
        modificado=bool(fila["modificado"]),
    )


def _listar_versiones(con: sqlite3.Connection, *, novel_id: str) -> list[VersionResumen]:
    _exigir_novela(con, novel_id)
    return [_resumen(con, f) for f in repository.listar_versiones(con, novel_id=novel_id)]


def _obtener_version(con: sqlite3.Connection, *, novel_id: str, version: int) -> Version:
    fila = _exigir_version(con, novel_id, version)
    brief = leer_brief(con, novel_id=novel_id)
    capitulos = repository.capitulos_de_version(con, novel_id=novel_id, version=version)
    return Version(
        version=fila["version"],
        novel_id=novel_id,
        titulo=fila["titulo"],
        publicada_en=fila["publicada_en"],
        version_anterior=fila["version_anterior"],
        hash=fila["hash"],
        dedicatoria=None if brief is None else brief.dedicatoria,
        capitulos=[
            CapituloIndice(
                numero=c["numero"],
                titulo=c["titulo"],
                palabras=c["palabras"],
                modificado=bool(c["modificado"]),
            )
            for c in capitulos
        ],
    )


def _listar_capitulos(con: sqlite3.Connection, *, novel_id: str, version: int) -> list[Capitulo]:
    _exigir_version(con, novel_id, version)
    return [
        _capitulo(f)
        for f in repository.capitulos_de_version(con, novel_id=novel_id, version=version)
    ]


def _obtener_capitulo(
    con: sqlite3.Connection, *, novel_id: str, version: int, numero: int
) -> Capitulo:
    for c in _listar_capitulos(con, novel_id=novel_id, version=version):
        if c.numero == numero:
            return c
    raise VersionNoEncontrada(
        f"la versión {version} de la novela {novel_id} no tiene el capítulo {numero}",
        novel_id=novel_id,
        capitulo=numero,
    )


async def listar_versiones(db: BaseDatos, novel_id: str) -> list[VersionResumen]:
    return await db.ejecutar(partial(_listar_versiones, novel_id=novel_id))


async def obtener_version(db: BaseDatos, novel_id: str, version: int) -> Version:
    return await db.ejecutar(partial(_obtener_version, novel_id=novel_id, version=version))


async def listar_capitulos(db: BaseDatos, novel_id: str, version: int) -> list[Capitulo]:
    return await db.ejecutar(partial(_listar_capitulos, novel_id=novel_id, version=version))


async def obtener_capitulo(db: BaseDatos, novel_id: str, version: int, numero: int) -> Capitulo:
    return await db.ejecutar(
        partial(_obtener_capitulo, novel_id=novel_id, version=version, numero=numero)
    )
