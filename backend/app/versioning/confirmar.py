"""Confirmar una solicitud de cambio: retcon, obsolescencia y regeneración dirigida
(RF-VER-08).

Todo en una transacción: el hecho viejo se cierra por vigencia y el nuevo se abre en la
versión candidata, los capítulos del análisis de impacto —y **solo** esos— tienen en ella una
fila nueva que nace `Obsoleto`, y se encola una generación `dirigida` que la reescribirá. La
versión publicada no se toca, ni el estado de sus filas: sigue leyendo el hecho viejo y sus
mismos textos (regla 15, TO-062). La candidata parte siempre de la vigente y toma el primer
número libre: una candidata rechazada conserva el suyo.
"""

from __future__ import annotations

import json
import sqlite3

from app.canon import service as canon
from app.commons.errores import (
    GeneracionEnCurso,
    HechoNoEncontrado,
    NovelaNoEncontrada,
    TransicionInvalida,
)
from app.commons.recursos import Recursos
from app.commons.tiempo import ahora
from app.novel import service as novel
from app.process import service as process
from app.versioning import repository


async def confirmar(r: Recursos, novel_id: str, solicitud_id: str) -> process.Generacion:
    def escribir(con: sqlite3.Connection) -> process.Generacion:
        if novel.estado_de_obra(con, novel_id=novel_id) is None:
            raise NovelaNoEncontrada(novel_id=novel_id)
        fila = repository.leer_solicitud(con, novel_id=novel_id, solicitud_id=solicitud_id)
        if fila is None:
            raise NovelaNoEncontrada(f"la solicitud {solicitud_id} no existe", novel_id=novel_id)
        if fila["estado"] != "pendiente-de-confirmacion":
            raise TransicionInvalida(
                f"la solicitud está {fila['estado']}: solo se confirma una pendiente",
                novel_id=novel_id,
            )
        vivo = process.trabajo_vivo(con, novel_id=novel_id)
        if vivo is not None:
            raise GeneracionEnCurso(novel_id=novel_id, generacion_id=vivo)
        hecho_id = fila["hecho_id"] or fila["hecho_candidato_id"]
        if hecho_id is None or fila["capitulos_afectados"] is None:
            raise HechoNoEncontrado(
                "la solicitud no tiene un hecho que cambiar: selecciona uno", novel_id=novel_id
            )
        version = fila["version_base"]
        if novel.version_vigente(con, novel_id=novel_id) != version:
            raise TransicionInvalida(
                "la novela ya tiene otra versión: pide el cambio sobre la vigente",
                novel_id=novel_id,
            )
        nueva = repository.siguiente_version(con, novel_id=novel_id, version=version)
        momento = ahora()
        canon.aplicar_retcon(
            con,
            novel_id=novel_id,
            solicitud_id=solicitud_id,
            hecho_id=hecho_id,
            enunciado_nuevo=fila["enunciado_nuevo"],
            version_nueva=nueva,
            ahora=momento,
        )
        afectados: list[int] = json.loads(fila["capitulos_afectados"])
        for numero in afectados:
            # La marca vive en la candidata: la fila publicada sigue `Aceptado` (TO-062).
            novel.crear_capitulo(
                con, novel_id=novel_id, numero=numero, version=nueva, estado="Obsoleto"
            )
        generacion = process.encolar(
            con,
            r,
            novel_id=novel_id,
            tipo="dirigida",
            accion="Regenerar",
            version_objetivo=nueva,
            capitulos_a_regenerar=afectados,
            solicitud_id=solicitud_id,
        )
        repository.fijar_estado_solicitud(
            con, novel_id=novel_id, solicitud_id=solicitud_id, estado="confirmada"
        )
        return generacion

    generacion = await r.db.en_transaccion(escribir)
    if r.avisar_trabajo is not None:
        r.avisar_trabajo()
    return generacion
