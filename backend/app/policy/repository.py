"""SQL del audit log y de las coincidencias. El audit log solo se inserta: no hay aquí, ni en
ningún otro sitio del código, una sentencia que lo modifique (RF-POL-02)."""

from __future__ import annotations

import sqlite3
import uuid

from pydantic import BaseModel, ConfigDict


class DecisionRegistrada(BaseModel):
    """Una fila del audit log: una `Decisión de policy`."""

    model_config = ConfigDict(frozen=True)

    momento: str
    sujeto: str
    sujeto_id: str
    regla: str
    entrada: str
    resultado: str


def insertar_decision(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    sujeto: str,
    sujeto_id: str,
    regla: str,
    entrada: str,
    resultado: str,
    momento: str,
) -> None:
    con.execute(
        "INSERT INTO audit_log"
        " (id, novel_id, momento, sujeto, sujeto_id, regla, entrada, resultado)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), novel_id, momento, sujeto, sujeto_id, regla, entrada, resultado),
    )


def insertar_coincidencia(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    capitulo_id: str,
    palabra: str,
    nivel: str,
    inicio: int,
    fin: int,
    intento: int,
) -> None:
    con.execute(
        "INSERT INTO coincidencia (id, novel_id, capitulo_id, palabra, nivel, inicio, fin, intento)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), novel_id, capitulo_id, palabra, nivel, inicio, fin, intento),
    )


def leer_decisiones(con: sqlite3.Connection, *, novel_id: str) -> list[DecisionRegistrada]:
    filas = con.execute(
        "SELECT momento, sujeto, sujeto_id, regla, entrada, resultado FROM audit_log"
        " WHERE novel_id = ? ORDER BY momento, rowid",
        (novel_id,),
    ).fetchall()
    return [DecisionRegistrada(**dict(f)) for f in filas]
