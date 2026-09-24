"""Cerrojo de instancia única sobre la base (RF-PROC-03, D-11).

El pool en vuelo es un semáforo **en proceso**: dos procesos contra la misma base lo
duplicarían en silencio y la instancia podría tener el doble de tokens en vuelo. El cerrojo
lo convierte en un fallo en voz alta al arrancar.

Es un fichero SQLite hermano de la base con una transacción `EXCLUSIVE` abierta mientras
vive el proceso: el sistema operativo lo suelta si el proceso muere, así que una caída no
deja un cerrojo huérfano que impida volver a arrancar.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


class InstanciaYaEnMarcha(RuntimeError):
    """Otro proceso tiene abierta esta misma base."""


class CerrojoInstancia:
    def __init__(self, ruta_db: Path) -> None:
        self.ruta = ruta_db.with_name(ruta_db.name + ".instancia")
        self._con: sqlite3.Connection | None = None

    def adquirir(self) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.ruta, timeout=0, isolation_level=None)
        try:
            con.execute("PRAGMA locking_mode = EXCLUSIVE")
            con.execute("BEGIN EXCLUSIVE")
        except sqlite3.OperationalError as e:
            con.close()
            raise InstanciaYaEnMarcha(
                f"ya hay una instancia del backend usando {self.ruta.with_suffix('')}: "
                "arrancar dos duplicaría el presupuesto en vuelo. Un solo proceso, un solo "
                "worker (README)"
            ) from e
        self._con = con

    def liberar(self) -> None:
        if self._con is not None:
            try:
                self._con.execute("ROLLBACK")
            finally:
                self._con.close()
                self._con = None
