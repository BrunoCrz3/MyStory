"""Portada de una versión: su título, la dedicatoria del brief, a quién va y por qué
(RF-VER-05)."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.intake.service import leer_brief
from app.versioning.schemas import Portada

_OCASIONES = {
    "cumpleanos": "cumpleaños",
    "boda": "boda",
    "aniversario": "aniversario",
    "jubilacion": "jubilación",
    "nacimiento": "nacimiento",
    "otra": None,
}


def portada(con: sqlite3.Connection, *, novel_id: str, version_fila: dict[str, Any]) -> Portada:
    brief = leer_brief(con, novel_id=novel_id)
    assert brief is not None, "una versión publicada siempre tiene brief"
    return Portada(
        titulo=version_fila["titulo"] or "",
        dedicatoria=brief.dedicatoria,
        destinatario=brief.destinatario.nombre,
        ocasion=_OCASIONES[brief.ocasion.tipo],
    )
