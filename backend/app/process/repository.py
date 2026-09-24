"""SQL de `process/`: el esquema (restricciones de destino)."""

from __future__ import annotations

import sqlite3
import uuid


def insertar_restriccion(
    con: sqlite3.Connection, *, novel_id: str, numero: int, tipo: str, enunciado: str, alcance: str
) -> str:
    restriccion_id = str(uuid.uuid4())
    con.execute(
        "INSERT INTO restriccion_destino (id, novel_id, numero, tipo, enunciado, alcance)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (restriccion_id, novel_id, numero, tipo, enunciado, alcance),
    )
    return restriccion_id


def hay_esquema(con: sqlite3.Connection, *, novel_id: str) -> bool:
    return (
        con.execute("SELECT 1 FROM restriccion_destino WHERE novel_id = ?", (novel_id,)).fetchone()
        is not None
    )
