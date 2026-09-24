"""SQL explícito de la obra. Nadie de fuera de `novel/` importa este módulo."""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from app.intake.service import BriefNovela
from app.novel.models import ReglaMundo

# Listar todas las novelas es, por definición, una consulta que no acota a una (A-02).
CONSULTAS_TRANSVERSALES = {"listar_obras", "contar_obras"}


def insertar_obra(
    con: sqlite3.Connection, *, novel_id: str, brief: BriefNovela, total: int, ahora: str
) -> None:
    con.execute(
        "INSERT INTO obra (novel_id, premisa, genero, tono, total_capitulos, creada_en)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (novel_id, brief.premisa, brief.genero, brief.tono, total, ahora),
    )
    con.executemany(
        "INSERT INTO regla_mundo (id, novel_id, orden, enunciado, origen)"
        " VALUES (?, ?, ?, ?, 'brief')",
        [(uuid.uuid4().hex, novel_id, i, r) for i, r in enumerate(brief.reglas_mundo)],
    )
    v = brief.voz_narrativa
    con.execute(
        "INSERT INTO voz_narrativa (novel_id, persona, tiempo_verbal, focalizacion)"
        " VALUES (?, ?, ?, ?)",
        (novel_id, v.persona, v.tiempo_verbal, v.focalizacion),
    )


def leer_obra(con: sqlite3.Connection, *, novel_id: str) -> dict[str, Any] | None:
    fila = con.execute(
        "SELECT novel_id, titulo, estado, total_capitulos, creada_en FROM obra WHERE novel_id = ?",
        (novel_id,),
    ).fetchone()
    return None if fila is None else dict(fila)


def listar_obras(
    con: sqlite3.Connection, *, limite: int, desplazamiento: int
) -> list[dict[str, Any]]:
    filas = con.execute(
        "SELECT novel_id, titulo, estado, creada_en FROM obra"
        " ORDER BY creada_en DESC, rowid DESC LIMIT ? OFFSET ?",
        (limite, desplazamiento),
    ).fetchall()
    return [dict(f) for f in filas]


def contar_obras(con: sqlite3.Connection) -> int:
    total: int = con.execute("SELECT count(*) FROM obra").fetchone()[0]
    return total


def leer_reglas(con: sqlite3.Connection, *, novel_id: str) -> list[ReglaMundo]:
    filas = con.execute(
        "SELECT enunciado, origen FROM regla_mundo WHERE novel_id = ? ORDER BY orden", (novel_id,)
    ).fetchall()
    return [ReglaMundo(enunciado=f["enunciado"], origen=f["origen"]) for f in filas]


def insertar_capitulo(con: sqlite3.Connection, *, novel_id: str, numero: int, version: int) -> str:
    capitulo_id = str(uuid.uuid4())
    con.execute(
        "INSERT INTO capitulo (id, novel_id, numero, version) VALUES (?, ?, ?, ?)",
        (capitulo_id, novel_id, numero, version),
    )
    return capitulo_id
