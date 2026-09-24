"""Versiones de la novela: candidata, gate de publicación, publicación inmutable y lectura.

La versión se escribe `candidata` con sus vínculos, y el hash del contenido es lo que hace
comprobable que después no cambia (RNF-07). El gate corre sin modelo sobre ella
(`architecture.md` § Hooks y policy engine), `render_visual` incluido, y solo si todo pasa la
versión se publica; si no, queda `rechazada` (TO-045, RNF-19).
"""

from __future__ import annotations

import sqlite3
from functools import partial
from typing import Any

from app.commons.config import Config
from app.commons.db import BaseDatos
from app.commons.errores import NovelaNoEncontrada, TransicionInvalida, VersionNoEncontrada
from app.commons.tiempo import ahora
from app.intake.service import leer_brief
from app.novel import service as novel
from app.process import service as process
from app.process.service import VeredictoGate
from app.versioning import ficha as _ficha
from app.versioning import gate, repository
from app.versioning import portada as _portada
from app.versioning.huella import contenido, hash_contenido, hash_de_version
from app.versioning.render_visual import RenderVisual, SinNavegador, render_de_entorno
from app.versioning.schemas import (
    Capitulo,
    CapituloIndice,
    Ficha,
    Portada,
    Version,
    VersionResumen,
)

__all__ = [
    "Capitulo",
    "Publicacion",
    "RenderVisual",
    "SinNavegador",
    "Version",
    "VersionResumen",
    "hash_de_version",
    "listar_capitulos",
    "listar_versiones",
    "obtener_capitulo",
    "obtener_version",
    "render_de_entorno",
]


def candidatos(con: sqlite3.Connection, *, novel_id: str, version: int) -> dict[int, str]:
    """Qué fila de capítulo leerá cada número en la versión que se va a publicar.

    Los aceptados de esta versión; para los que no se reescribieron, la fila que ya leía la
    versión anterior (D-05).
    """
    anteriores = (
        repository.vinculos(con, novel_id=novel_id, version=version - 1) if version > 1 else {}
    )
    nuevos = repository.aceptados_de_version(con, novel_id=novel_id, version=version)
    return {**anteriores, **{n: str(f["id"]) for n, f in nuevos.items()}}


class Publicacion:
    """Implementación del puerto `Publicador` de `process/` (TO-045).

    `render` es el puerto de `render_visual`; sin él, `SinNavegador`, que no deja publicar.
    """

    def __init__(self, config: Config, render: RenderVisual | None = None) -> None:
        self.config = config
        self.render: RenderVisual = render if render is not None else SinNavegador()

    def proponer(
        self, con: sqlite3.Connection, *, novel_id: str, version: int, generacion_id: str
    ) -> str:
        existente = repository.leer_version(con, novel_id=novel_id, version=version)
        if existente is not None:
            # A-115: una reanudación encuentra la candidata ya escrita y la reutiliza; sus
            # capítulos están aceptados y su contenido no ha cambiado.
            if existente["estado"] != "candidata":
                raise TransicionInvalida(
                    f"la versión {version} ya está {existente['estado']}", novel_id=novel_id
                )
            return str(existente["hash"])
        filas = candidatos(con, novel_id=novel_id, version=version)
        anterior = (
            repository.leer_version(con, novel_id=novel_id, version=version - 1)
            if version > 1
            else None
        )
        previos = (
            repository.vinculos(con, novel_id=novel_id, version=version - 1) if anterior else {}
        )
        titulo = novel.titulo_de_obra(con, novel_id=novel_id)
        huella = hash_contenido(titulo, contenido(con, novel_id=novel_id, ids=list(filas.values())))
        repository.insertar_version(
            con,
            novel_id=novel_id,
            version=version,
            version_anterior_id=None if anterior is None else anterior["id"],
            titulo=titulo,
            hash_contenido=huella,
            motivo=None,
            generacion_id=generacion_id,
            ahora=ahora(),
        )
        for numero, capitulo_id in sorted(filas.items()):
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

    def gate(self, con: sqlite3.Connection, *, novel_id: str, version: int) -> list[VeredictoGate]:
        filas = candidatos(con, novel_id=novel_id, version=version)
        ids = list(filas.values())
        capitulos = contenido(con, novel_id=novel_id, ids=ids)
        veredictos = [
            gate.estructura_edicion(con, novel_id=novel_id, capitulos=capitulos),
            gate.elementos_obligatorios(con, novel_id=novel_id, ids=ids),
            gate.cierre_arco(self.config, con, novel_id=novel_id, version=version, ids=ids),
        ]
        if version > 1:
            # D-17: desde la segunda versión, el gate comprueba que la regeneración fue fiel.
            veredictos.append(
                gate.regeneracion_fiel(con, novel_id=novel_id, version=version, candidatos=filas)
            )
        return veredictos

    async def render_visual(self, *, novel_id: str, version: int) -> VeredictoGate:
        return await self.render(novel_id=novel_id, version=version)

    def publicar(self, con: sqlite3.Connection, *, novel_id: str, version: int) -> None:
        repository.decidir_version(
            con, novel_id=novel_id, version=version, estado="publicada", ahora=ahora()
        )
        # Una regeneración dirigida cierra la solicitud que la pidió (RF-VER-08).
        fila = repository.leer_version(con, novel_id=novel_id, version=version)
        assert fila is not None and fila["estado"] == "publicada"
        solicitud_id = process.solicitud_de_trabajo(
            con, novel_id=novel_id, trabajo_id=fila["generacion_id"]
        )
        if solicitud_id is not None:
            repository.aplicar_solicitud(
                con, novel_id=novel_id, solicitud_id=solicitud_id, version_resultante=version
            )

    def rechazar(self, con: sqlite3.Connection, *, novel_id: str, version: int) -> None:
        repository.decidir_version(
            con, novel_id=novel_id, version=version, estado="rechazada", ahora=ahora()
        )


# --- Lectura ---------------------------------------------------------------------------


def _exigir_novela(con: sqlite3.Connection, novel_id: str) -> None:
    if novel.estado_de_obra(con, novel_id=novel_id) is None:
        raise NovelaNoEncontrada(f"no existe la novela {novel_id}", novel_id=novel_id)


def _exigir_version(con: sqlite3.Connection, novel_id: str, version: int) -> dict[str, Any]:
    _exigir_novela(con, novel_id)
    fila = repository.leer_version(con, novel_id=novel_id, version=version)
    if fila is None:
        raise VersionNoEncontrada(
            f"la novela {novel_id} no tiene la versión {version}", novel_id=novel_id
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
        estado=fila["estado"],
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


async def obtener_ficha(db: BaseDatos, novel_id: str, version: int) -> Ficha:
    def leer(con: sqlite3.Connection) -> Ficha:
        _exigir_version(con, novel_id, version)
        return _ficha.ficha(con, novel_id=novel_id, version=version)

    return await db.ejecutar(leer)


async def obtener_portada(db: BaseDatos, novel_id: str, version: int) -> Portada:
    def leer(con: sqlite3.Connection) -> Portada:
        fila = _exigir_version(con, novel_id, version)
        return _portada.portada(con, novel_id=novel_id, version_fila=fila)

    return await db.ejecutar(leer)
