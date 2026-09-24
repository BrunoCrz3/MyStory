"""SQL de `context/`: brief de capítulo y resumen de capítulo."""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any


def insertar_brief_capitulo(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    brief_id: str,
    numero: int,
    restriccion_id: str,
    titulo_provisional: str,
    funcion_dramatica: str,
    pov: str,
    lugar: str,
    estado_entrada: str,
    elementos: str,
) -> str:
    con.execute(
        "INSERT INTO brief_capitulo (id, novel_id, numero, restriccion_id, titulo_provisional,"
        " funcion_dramatica, pov, lugar, estado_entrada, elementos)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            brief_id,
            novel_id,
            numero,
            restriccion_id,
            titulo_provisional,
            funcion_dramatica,
            pov,
            lugar,
            estado_entrada,
            elementos,
        ),
    )
    return brief_id


def leer_brief_capitulo(
    con: sqlite3.Connection, *, novel_id: str, numero: int
) -> dict[str, Any] | None:
    fila = con.execute(
        "SELECT b.numero, b.titulo_provisional, b.funcion_dramatica, b.pov, b.lugar,"
        " b.estado_entrada, b.elementos, r.tipo, r.enunciado, r.alcance"
        " FROM brief_capitulo b JOIN restriccion_destino r ON r.id = b.restriccion_id"
        " WHERE b.novel_id = ? AND b.numero = ?",
        (novel_id, numero),
    ).fetchone()
    return None if fila is None else dict(fila)


def insertar_resumen(
    con: sqlite3.Connection, *, novel_id: str, capitulo_id: str, texto: str
) -> None:
    con.execute(
        "INSERT OR IGNORE INTO resumen_capitulo (id, novel_id, capitulo_id, texto)"
        " VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), novel_id, capitulo_id, texto),
    )


def leer_resumen(con: sqlite3.Connection, *, novel_id: str, capitulo_id: str) -> str | None:
    fila = con.execute(
        "SELECT texto FROM resumen_capitulo WHERE novel_id = ? AND capitulo_id = ?",
        (novel_id, capitulo_id),
    ).fetchone()
    return None if fila is None else str(fila["texto"])
