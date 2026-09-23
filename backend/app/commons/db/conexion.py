"""Unica fabrica de conexiones a `data/novel.db`.

Es unica a proposito. El punto ciego que `docs/verification.md` anota en A-18 es
que una conexion abierta aparte —una migracion suelta, un script— puede no
llevar `WAL`; si solo hay una puerta, no hay aparte.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import sqlite_vec

from app.commons.config import raiz_del_repositorio

Conexion = sqlite3.Connection

VARIABLE_DE_ENTORNO = "MYSTORY_DB"


def ruta_de_la_base() -> Path:
    declarada = os.environ.get(VARIABLE_DE_ENTORNO)
    if declarada:
        return Path(declarada)
    return raiz_del_repositorio() / "data" / "novel.db"


def crear_conexion(ruta: Path | None = None) -> Conexion:
    """Abre la base con los ajustes que el resto del sistema da por hechos.

    - `WAL` (RNF-02, A-18): leer mientras se escribe.
    - Claves foraneas: SQLite las ignora por defecto, y un `REFERENCES` que no
      se aplica es documentacion, no integridad.
    - `isolation_level = None`: sin transacciones implicitas de la libreria. El
      SQL es explicito, incluido el `BEGIN`.
    - `sqlite-vec` cargado: las tablas `vec0` viven en el mismo fichero.
    """
    destino = ruta or ruta_de_la_base()
    destino.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(destino, isolation_level=None)
    conexion.row_factory = sqlite3.Row
    # `sqlite-vec` se carga aqui y solo aqui, por el mismo motivo que `WAL`: una
    # conexion abierta aparte no veria las tablas `vec0` y fallaria al leer el
    # indice, no al abrirlo.
    conexion.enable_load_extension(True)
    sqlite_vec.load(conexion)
    conexion.enable_load_extension(False)
    conexion.execute("PRAGMA journal_mode = WAL")
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


@contextmanager
def abrir_conexion(ruta: Path | None = None) -> Iterator[Conexion]:
    conexion = crear_conexion(ruta)
    try:
        yield conexion
    finally:
        conexion.close()


@contextmanager
def transaccion(conexion: Conexion) -> Iterator[Conexion]:
    """Toda escritura al canon va en transaccion (RNF-02, A-17)."""
    conexion.execute("BEGIN")
    try:
        yield conexion
    except BaseException:
        conexion.execute("ROLLBACK")
        raise
    conexion.execute("COMMIT")
