"""Cola de generaciones en SQLite (TO-030) y el recurso `Generacion` (RF-PROC-01, 02, 04, 05).

Encolar es barato y responde enseguida: el trabajo largo lo hace el worker. Antes de encolar
se comprueba lo que haría imposible el trabajo —una generación viva, una transición que la
máquina no admite, una estimación que no cabe en el pool (RNF-03)— para fallar en voz alta
en la petición y no minutos después dentro del worker.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from functools import partial
from typing import Any

from app.commons.errores import GeneracionEnCurso, NovelaNoEncontrada
from app.commons.recursos import Recursos
from app.commons.tiempo import ahora
from app.novel import service as novel
from app.process import repository
from app.process.schemas import Generacion
from app.process.transiciones import aplicar

TERMINALES = frozenset({"Publicada", "Detenida"})


def es_terminal(estado: str) -> bool:
    return estado in TERMINALES


def reclamar(con: sqlite3.Connection) -> str | None:
    """Reclama el trabajo pendiente más antiguo; `None` si no hay o si otro lo ganó."""
    return repository.reclamar_siguiente(con)


def _vista(con: sqlite3.Connection, r: Recursos, t: dict[str, Any]) -> Generacion:
    novel_id = t["novel_id"]
    total = novel.total_capitulos(con, novel_id=novel_id)
    a_regenerar: list[int] = json.loads(t["capitulos_a_regenerar"])
    aceptados = novel.contar_aceptados(con, novel_id=novel_id, version=t["version_objetivo"])
    if t["tipo"] == "dirigida":
        aceptados = total - len(a_regenerar) + aceptados
    intentos = None
    if t["capitulo_actual"] is not None:
        cap = novel.capitulo_en_curso(
            con, novel_id=novel_id, numero=t["capitulo_actual"], version=t["version_objetivo"]
        )
        intentos = cap.intentos if cap is not None else 0
    terminal = es_terminal(t["estado"])
    return Generacion(
        generacion_id=t["id"],
        novel_id=novel_id,
        tipo=t["tipo"],
        estado=t["estado"],
        es_terminal=terminal,
        intervalo_sondeo_segundos=None
        if terminal
        else r.config.umbrales.orquestacion.intervalo_sondeo_segundos,
        capitulo_actual=t["capitulo_actual"],
        capitulos_aceptados=aceptados,
        total_capitulos=total,
        capitulos_a_regenerar=a_regenerar if t["tipo"] == "dirigida" else None,
        intentos_capitulo_actual=intentos if intentos is not None else 0,
        checkpoint=t["ultimo_capitulo"],
        tokens_consumidos=t["tokens_consumidos"],
        coste_usd=t["coste_usd"],
        traza_langfuse_id=t["traza_langfuse_id"],
        detenida_por=t["detenida_por"],
        version_resultante=t["version_resultante"],
        iniciada_en=t["iniciada_en"],
        terminada_en=t["terminada_en"],
    )


def encolar(
    con: sqlite3.Connection,
    r: Recursos,
    *,
    novel_id: str,
    tipo: str,
    accion: str,
    version_objetivo: int,
    capitulos_a_regenerar: list[int] | None = None,
    solicitud_id: str | None = None,
) -> Generacion:
    """Encola una generación dentro de la transacción del llamante."""
    estado = novel.estado_de_obra(con, novel_id=novel_id)
    if estado is None:
        raise NovelaNoEncontrada(f"no existe la novela {novel_id}", novel_id=novel_id)
    vivo = repository.trabajo_vivo(con, novel_id=novel_id)
    if vivo is not None:
        raise GeneracionEnCurso(
            "consulta su progreso en lugar de lanzar otra", novel_id=novel_id, generacion_id=vivo
        )
    aplicar("Novela", estado, accion)
    # La estimación de un trabajo es la de su llamada más grande, que ya incluye el margen de
    # respuesta: nunca más que el límite por petición (architecture.md § Presupuesto).
    estimacion = r.config.umbrales.contexto.total
    r.pool.comprobar(estimacion)
    trabajo_id = str(uuid.uuid4())
    repository.insertar_trabajo(
        con,
        novel_id=novel_id,
        trabajo_id=trabajo_id,
        tipo=tipo,
        estado=estado,
        version_objetivo=version_objetivo,
        estimacion=estimacion,
        capitulos_a_regenerar=json.dumps(capitulos_a_regenerar or []),
        solicitud_id=solicitud_id,
        ahora=ahora(),
    )
    t = repository.leer_trabajo(con, novel_id=novel_id, trabajo_id=trabajo_id)
    assert t is not None
    return _vista(con, r, t)


async def lanzar_generacion(r: Recursos, novel_id: str) -> Generacion:
    def escribir(con: sqlite3.Connection) -> Generacion:
        vigente = novel.version_vigente(con, novel_id=novel_id)
        return encolar(
            con,
            r,
            novel_id=novel_id,
            tipo="inicial",
            accion="Planificar",
            version_objetivo=(vigente or 0) + 1,
        )

    try:
        generacion = await r.db.en_transaccion(escribir)
    except sqlite3.IntegrityError as e:
        # Dos lanzamientos a la vez: el índice único de trabajos vivos dejó entrar a uno.
        vivo = await r.db.ejecutar(partial(repository.trabajo_vivo, novel_id=novel_id))
        raise GeneracionEnCurso(
            "consulta su progreso en lugar de lanzar otra", novel_id=novel_id, generacion_id=vivo
        ) from e
    if r.avisar_trabajo is not None:
        r.avisar_trabajo()
    return generacion


async def obtener_generacion(r: Recursos, novel_id: str, generacion_id: str) -> Generacion:
    def leer(con: sqlite3.Connection) -> Generacion:
        if novel.estado_de_obra(con, novel_id=novel_id) is None:
            raise NovelaNoEncontrada(f"no existe la novela {novel_id}", novel_id=novel_id)
        t = repository.leer_trabajo(con, novel_id=novel_id, trabajo_id=generacion_id)
        if t is None:
            raise NovelaNoEncontrada(
                f"la novela {novel_id} no tiene la generación {generacion_id}",
                novel_id=novel_id,
                generacion_id=generacion_id,
            )
        return _vista(con, r, t)

    return await r.db.ejecutar(leer)


async def listar_generaciones(r: Recursos, novel_id: str) -> list[Generacion]:
    def leer(con: sqlite3.Connection) -> list[Generacion]:
        if novel.estado_de_obra(con, novel_id=novel_id) is None:
            raise NovelaNoEncontrada(f"no existe la novela {novel_id}", novel_id=novel_id)
        return [_vista(con, r, t) for t in repository.listar_trabajos(con, novel_id=novel_id)]

    return await r.db.ejecutar(leer)


async def trabajos_en_cola(r: Recursos) -> int:
    return await r.db.ejecutar(repository.contar_en_cola)
