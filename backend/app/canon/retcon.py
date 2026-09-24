"""Retcon: cierra un hecho por vigencia y abre el que lo sustituye (RF-CANON-05, TO-028).

Nada se borra ni se sobrescribe: el hecho viejo sigue siendo verdad en las versiones que
ya existen, porque su `version_hasta` es la versión nueva y la vigencia es semiabierta (D-06).
El nuevo nace en esa versión. Va en la transacción de quien confirma la solicitud, con su
fila de `retcon`, o no ocurre nada.
"""

from __future__ import annotations

import sqlite3
import uuid

from app.commons.errores import HechoNoEncontrado


def aplicar_retcon(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    solicitud_id: str,
    hecho_id: str,
    enunciado_nuevo: str,
    version_nueva: int,
    ahora: str,
) -> str:
    viejo = con.execute(
        "SELECT tipo FROM hecho WHERE novel_id = ? AND id = ? AND version_hasta IS NULL",
        (novel_id, hecho_id),
    ).fetchone()
    if viejo is None:
        raise HechoNoEncontrado(
            f"el hecho {hecho_id} ya no está abierto: no se puede retconear", novel_id=novel_id
        )
    # RD-05: los usos caben en la vigencia de su hecho, así que se cierran primero. En la
    # versión nueva, los capítulos que se reescriban usarán el hecho nuevo, no este.
    con.execute(
        "UPDATE hecho_capitulo SET version_hasta = ?"
        " WHERE novel_id = ? AND hecho_id = ? AND version_hasta IS NULL",
        (version_nueva, novel_id, hecho_id),
    )
    con.execute(
        "UPDATE hecho SET estado = 'retconeado', version_hasta = ? WHERE novel_id = ? AND id = ?",
        (version_nueva, novel_id, hecho_id),
    )
    nuevo_id = str(uuid.uuid4())
    # El cambio lo pide el comprador, como el brief: `origen` no tiene otro valor para un
    # dato suyo, y la fila de `retcon` dice de dónde viene (A-99).
    con.execute(
        "INSERT INTO hecho (id, novel_id, enunciado, tipo, estado, origen, version_desde,"
        " creado_en) VALUES (?, ?, ?, ?, 'adoptado', 'brief', ?, ?)",
        (nuevo_id, novel_id, enunciado_nuevo, viejo["tipo"], version_nueva, ahora),
    )
    con.execute(
        "INSERT INTO retcon (id, novel_id, solicitud_id, hecho_viejo_id, hecho_nuevo_id,"
        " version, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), novel_id, solicitud_id, hecho_id, nuevo_id, version_nueva, ahora),
    )
    return nuevo_id
