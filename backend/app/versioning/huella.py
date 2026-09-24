"""El hash de una versión: SHA-256 de su contenido canónico (RNF-07).

Lo usan la publicación, para fijarlo, y el gate, para comprobar que la versión anterior
sigue intacta antes de publicar la siguiente (`regeneracion_fiel`).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

from app.commons.errores import VersionNoEncontrada
from app.versioning import repository


def hash_contenido(titulo: str | None, capitulos: list[dict[str, Any]]) -> str:
    """SHA-256 del contenido canónico: título de la obra y, en orden, número, título y texto."""
    canonico = {
        "titulo": titulo,
        "capitulos": [
            {"numero": c["numero"], "titulo": c["titulo"], "texto": c["texto"]}
            for c in sorted(capitulos, key=lambda c: int(c["numero"]))
        ],
    }
    datos = json.dumps(canonico, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(datos.encode("utf-8")).hexdigest()


def contenido(con: sqlite3.Connection, *, novel_id: str, ids: list[str]) -> list[dict[str, Any]]:
    return list(repository.contenido_de_capitulos(con, novel_id=novel_id, ids=ids).values())


def hash_de_version(con: sqlite3.Connection, *, novel_id: str, version: int) -> str:
    """Recalcula el hash de una versión publicada desde lo que lee hoy."""
    fila = repository.leer_version(con, novel_id=novel_id, version=version)
    if fila is None:
        raise VersionNoEncontrada(
            f"la novela {novel_id} no tiene la versión {version}", novel_id=novel_id
        )
    ids = list(repository.vinculos(con, novel_id=novel_id, version=version).values())
    return hash_contenido(fila["titulo"], contenido(con, novel_id=novel_id, ids=ids))
