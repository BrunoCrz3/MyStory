"""Conexiones a SQLite. `conectar()` es la única forma de abrir una, y por eso toda conexión
lleva `WAL` y claves foráneas (RD-04, D-03)."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TypeVar

import anyio.to_thread

RAIZ_REPO = Path(__file__).resolve().parents[4]
DB_POR_DEFECTO = RAIZ_REPO / "data" / "storymaker.db"

T = TypeVar("T")


def ruta_db() -> Path:
    """La base de `STORYMAKER_DB_PATH`. Una ruta relativa cuelga de la raíz del repositorio, no
    del directorio de trabajo: si no, arrancar desde `backend/` abriría otra base."""
    valor = os.environ.get("STORYMAKER_DB_PATH", "").strip()
    if not valor:
        return DB_POR_DEFECTO
    ruta = Path(valor)
    return ruta if ruta.is_absolute() else RAIZ_REPO / ruta


def conectar(ruta: Path) -> sqlite3.Connection:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    # `isolation_level=None`: sin transacciones implícitas. Toda escritura que toca más de
    # una fila va dentro de `transaccion()`, y así se ve en el código dónde empieza y acaba.
    con = sqlite3.connect(ruta, timeout=30, isolation_level=None, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 30000")
    return con


@contextmanager
def transaccion(con: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """`BEGIN IMMEDIATE` … `COMMIT`, o `ROLLBACK` si algo lanza. No se anida."""
    con.execute("BEGIN IMMEDIATE")
    try:
        yield con
    except BaseException:
        con.execute("ROLLBACK")
        raise
    con.execute("COMMIT")


class BaseDatos:
    """La base de una instancia. Abre una conexión por unidad de trabajo (D-03)."""

    def __init__(self, ruta: Path) -> None:
        self.ruta = ruta

    @contextmanager
    def conexion(self) -> Iterator[sqlite3.Connection]:
        con = conectar(self.ruta)
        try:
            yield con
        finally:
            con.close()

    def ejecutar_sync(self, fn: Callable[[sqlite3.Connection], T]) -> T:
        with self.conexion() as con:
            return fn(con)

    async def ejecutar(self, fn: Callable[[sqlite3.Connection], T]) -> T:
        """Ejecuta `fn(con)` en un hilo, para no bloquear el bucle de eventos."""
        return await anyio.to_thread.run_sync(self.ejecutar_sync, fn)

    def en_transaccion_sync(self, fn: Callable[[sqlite3.Connection], T]) -> T:
        with self.conexion() as con, transaccion(con):
            return fn(con)

    async def en_transaccion(self, fn: Callable[[sqlite3.Connection], T]) -> T:
        return await anyio.to_thread.run_sync(self.en_transaccion_sync, fn)
