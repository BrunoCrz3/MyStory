"""Lo que `process/` ofrece a otras features: el puerto de publicación.

El gate y la publicación son de `versioning/` (`architecture.md` § Hooks y policy engine),
pero quien decide cuándo corren es el orquestador. `versioning/` ya depende de `process/`
para encolar regeneraciones, así que `process/` no puede importarla: declara aquí lo que
necesita y el `lifespan` le inyecta la implementación.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Protocol

from app.process import repository
from app.process.cola import encolar
from app.process.schemas import Generacion
from app.process.transiciones import aplicar

__all__ = [
    "Generacion",
    "Publicador",
    "VeredictoGate",
    "aplicar",
    "encolar",
    "solicitud_de_trabajo",
    "trabajo_vivo",
]


@dataclass(frozen=True)
class VeredictoGate:
    """Resultado de un validador del gate de publicación, con su score."""

    nombre: str
    pasa: bool
    valor: float
    detalle: str


class Publicador(Protocol):
    """La versión nace `candidata`, el gate corre sobre ella y solo entonces se publica o se
    rechaza (TO-045, RNF-19). Los métodos síncronos corren en la transacción del llamante."""

    def proponer(
        self, con: sqlite3.Connection, *, novel_id: str, version: int, generacion_id: str
    ) -> str:
        """Escribe la versión `candidata` con sus vínculos, o reutiliza la que ya hay; devuelve
        su hash."""
        ...

    def gate(self, con: sqlite3.Connection, *, novel_id: str, version: int) -> list[VeredictoGate]:
        """Corre los validadores del gate que leen la base sobre la candidata."""
        ...

    async def render_visual(self, *, novel_id: str, version: int) -> VeredictoGate:
        """Pinta la candidata en la página `lectura` y afirma el contrato (TO-026)."""
        ...

    def publicar(self, con: sqlite3.Connection, *, novel_id: str, version: int) -> None:
        """La candidata pasa a `publicada`, y la solicitud que la pidió, a `aplicada`."""
        ...

    def rechazar(self, con: sqlite3.Connection, *, novel_id: str, version: int) -> None:
        """La candidata pasa a `rechazada`: nunca será la vigente."""
        ...


def trabajo_vivo(con: sqlite3.Connection, *, novel_id: str) -> str | None:
    """El trabajo pendiente o en curso de la novela, si lo hay: con él no se admite otro
    (RF-PROC-03) ni una solicitud de cambio (RF-VER-06)."""
    return repository.trabajo_vivo(con, novel_id=novel_id)


def solicitud_de_trabajo(con: sqlite3.Connection, *, novel_id: str, trabajo_id: str) -> str | None:
    """La solicitud de cambio que encoló un trabajo dirigido, si la hay."""
    fila = repository.leer_trabajo(con, novel_id=novel_id, trabajo_id=trabajo_id)
    if fila is None or fila["solicitud_id"] is None:
        return None
    return str(fila["solicitud_id"])
