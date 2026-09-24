"""Ficha de personajes y lugares de una versión (RF-VER-04).

Sale de la story bible de **esa** versión: las filas de capítulo que la versión lee deciden
dónde aparece cada entidad. Un capítulo reescrito en la versión 2 cambia la ficha de la 2 y
deja la de la 1 como estaba.
"""

from __future__ import annotations

import sqlite3

from app.novel import service as novel
from app.versioning import repository
from app.versioning.schemas import EntradaFicha, Ficha


def _descripcion(*partes: str | None) -> str | None:
    texto = ". ".join(p.strip().rstrip(".") for p in partes if p and p.strip())
    return f"{texto}." if texto else None


def ficha(con: sqlite3.Connection, *, novel_id: str, version: int) -> Ficha:
    vinculos = repository.vinculos(con, novel_id=novel_id, version=version)
    numero_de = {cid: n for n, cid in vinculos.items()}
    por_personaje, por_lugar = novel.apariciones(
        con, novel_id=novel_id, capitulo_ids=list(vinculos.values())
    )

    def capitulos(ids: set[str]) -> list[int]:
        return sorted(numero_de[cid] for cid in ids if cid in numero_de)

    return Ficha(
        personajes=[
            EntradaFicha(
                nombre=p.nombre,
                descripcion=_descripcion(p.rol_narrativo, p.deseo),
                capitulos=capitulos(por_personaje.get(p.nombre, set())),
            )
            for p in novel.personajes(con, novel_id=novel_id)
        ],
        lugares=[
            EntradaFicha(
                nombre=lugar.nombre,
                descripcion=_descripcion(lugar.atmosfera, lugar.geografia),
                capitulos=capitulos(por_lugar.get(lugar.nombre, set())),
            )
            for lugar in novel.lugares(con, novel_id=novel_id)
        ],
    )
