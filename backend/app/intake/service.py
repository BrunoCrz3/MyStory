"""Servicio del encargo: lo único de `intake/` que otra feature puede importar.

`intake/` es una hoja del grafo de importación: solo depende de `commons/` (D-08).
"""

from __future__ import annotations

import sqlite3

from app.intake import repository
from app.intake.schemas import (
    BriefNovela,
    Comprador,
    Dedicatoria,
    Destinatario,
    ElementoPersonalizado,
    Ocasion,
    TextoLibre,
    VozNarrativa,
)

__all__ = [
    "BriefNovela",
    "Comprador",
    "Dedicatoria",
    "Destinatario",
    "ElementoPersonalizado",
    "Ocasion",
    "TextoLibre",
    "VozNarrativa",
    "elementos_personalizados",
    "leer_brief",
    "registrar_brief",
]


def registrar_brief(
    con: sqlite3.Connection, *, novel_id: str, brief: BriefNovela, ahora: str
) -> None:
    """Persiste el brief validado. Va dentro de la transacción de quien crea la novela."""
    repository.insertar_brief(con, novel_id=novel_id, brief=brief, ahora=ahora)


def leer_brief(con: sqlite3.Connection, *, novel_id: str) -> BriefNovela | None:
    return repository.leer_brief(con, novel_id=novel_id)


def elementos_personalizados(
    con: sqlite3.Connection, *, novel_id: str
) -> list[tuple[str, str, bool]]:
    """`(id, enunciado, obligatorio)` de cada elemento personalizado del brief."""
    return repository.leer_elementos(con, novel_id=novel_id)
