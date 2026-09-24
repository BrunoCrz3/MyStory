"""Solicitud de cambio: se registra con su análisis de impacto y **no regenera nada**
(RF-VER-06, TO-011). El lector confirma aparte, y solo entonces se aplica el retcon."""

from __future__ import annotations

import json
import sqlite3
import uuid
from uuid import UUID

from app.canon import service as canon
from app.commons.db import BaseDatos
from app.commons.errores import (
    GeneracionEnCurso,
    HechoNoEncontrado,
    NovelaNoEncontrada,
    VersionNoEncontrada,
)
from app.commons.tiempo import ahora
from app.novel import service as novel
from app.process import service as process
from app.versioning import impacto, repository
from app.versioning.schemas import AnalisisImpacto, NuevaSolicitudCambio, SolicitudCambio


def _vigente(con: sqlite3.Connection, novel_id: str) -> int:
    if novel.estado_de_obra(con, novel_id=novel_id) is None:
        raise NovelaNoEncontrada(novel_id=novel_id)
    vigente = novel.version_vigente(con, novel_id=novel_id)
    if vigente is None:
        raise VersionNoEncontrada("la novela no tiene ninguna versión publicada", novel_id=novel_id)
    return vigente


def _hecho_vigente(hecho: canon.Hecho) -> canon.HechoVigente:
    return canon.HechoVigente(
        hecho_id=UUID(hecho.hecho_id),
        enunciado=hecho.enunciado,
        estado=hecho.estado,
        origen=hecho.origen,
        capitulo_establece=hecho.capitulo_establece,
        capitulos_usan=hecho.capitulos_usan,
        fragmento_soporte=hecho.fragmento_soporte,
    )


def _leer(con: sqlite3.Connection, novel_id: str, solicitud_id: str) -> SolicitudCambio:
    fila = repository.leer_solicitud(con, novel_id=novel_id, solicitud_id=solicitud_id)
    if fila is None:
        # El catálogo es cerrado y no tiene `solicitud-no-encontrada` (A-94).
        raise NovelaNoEncontrada(f"la solicitud {solicitud_id} no existe", novel_id=novel_id)
    vigentes = {
        h.hecho_id: h
        for h in canon.hechos_vigentes(con, novel_id=novel_id, version=fila["version_base"])
    }
    afectado = vigentes.get(fila["hecho_id"]) if fila["hecho_id"] else None
    candidato = vigentes.get(fila["hecho_candidato_id"]) if fila["hecho_candidato_id"] else None
    analisis = None
    if fila["capitulos_afectados"] is not None:
        analisis = AnalisisImpacto(
            capitulos_afectados=json.loads(fila["capitulos_afectados"]),
            hechos_derivados=json.loads(fila["hechos_derivados"]),
        )
    return SolicitudCambio(
        solicitud_id=UUID(fila["id"]),
        novel_id=UUID(novel_id),
        enunciado_nuevo=fila["enunciado_nuevo"],
        capitulo_origen=fila["capitulo_origen"],
        estado=fila["estado"],
        hecho_afectado=_hecho_vigente(afectado) if afectado else None,
        hecho_candidato=candidato.enunciado if candidato else None,
        analisis_impacto=analisis,
        version_resultante=fila["version_resultante"],
    )


async def crear_solicitud(
    db: BaseDatos, novel_id: str, nueva: NuevaSolicitudCambio
) -> SolicitudCambio:
    solicitud_id = str(uuid.uuid4())

    def escribir(con: sqlite3.Connection) -> SolicitudCambio:
        version = _vigente(con, novel_id)
        vivo = process.trabajo_vivo(con, novel_id=novel_id)
        if vivo is not None:
            raise GeneracionEnCurso(
                "espera a que termine antes de pedir un cambio",
                novel_id=novel_id,
                generacion_id=vivo,
            )
        vigentes = canon.hechos_vigentes(con, novel_id=novel_id, version=version)
        hecho = None
        if nueva.hecho_id is not None:
            hecho = next((h for h in vigentes if h.hecho_id == str(nueva.hecho_id)), None)
            if hecho is None:
                raise HechoNoEncontrado(
                    f"el hecho {nueva.hecho_id} no es vigente en la versión {version}",
                    novel_id=novel_id,
                )
        momento = ahora()
        repository.insertar_solicitud(
            con,
            solicitud_id=solicitud_id,
            novel_id=novel_id,
            version_base=version,
            hecho_id=hecho.hecho_id if hecho else None,
            fragmento=nueva.fragmento,
            enunciado_nuevo=nueva.enunciado_nuevo,
            capitulo_origen=nueva.capitulo_origen,
            ahora=momento,
        )
        if hecho is not None:
            analisis = impacto.analizar(hecho, vigentes)
            repository.insertar_analisis(
                con,
                novel_id=novel_id,
                solicitud_id=solicitud_id,
                capitulos=analisis.capitulos_afectados,
                derivados=[str(d) for d in analisis.hechos_derivados or []],
                ahora=momento,
            )
        return _leer(con, novel_id, solicitud_id)

    return await db.en_transaccion(escribir)


async def obtener_solicitud(db: BaseDatos, novel_id: str, solicitud_id: str) -> SolicitudCambio:
    def leer(con: sqlite3.Connection) -> SolicitudCambio:
        if novel.estado_de_obra(con, novel_id=novel_id) is None:
            raise NovelaNoEncontrada(novel_id=novel_id)
        return _leer(con, novel_id, solicitud_id)

    return await db.ejecutar(leer)
