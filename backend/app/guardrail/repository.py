"""SQL de las palabras prohibidas de nivel `novela`."""

from __future__ import annotations

import sqlite3
import uuid

from app.guardrail.models import PalabraProhibida


def insertar_palabras(
    con: sqlite3.Connection, *, novel_id: str, palabras: list[str], origen: str
) -> None:
    con.executemany(
        "INSERT INTO palabra_prohibida (id, novel_id, orden, forma, nivel, origen)"
        " VALUES (?, ?, ?, ?, 'novela', ?)",
        [(uuid.uuid4().hex, novel_id, i, p, origen) for i, p in enumerate(palabras)],
    )


def leer_palabras(con: sqlite3.Connection, *, novel_id: str) -> list[PalabraProhibida]:
    filas = con.execute(
        "SELECT forma, nivel, origen FROM palabra_prohibida WHERE novel_id = ? ORDER BY orden",
        (novel_id,),
    ).fetchall()
    return [PalabraProhibida(forma=f["forma"], nivel=f["nivel"], origen=f["origen"]) for f in filas]
