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


@dataclass(frozen=True)
class VeredictoGate:
    """Resultado de un validador del gate de publicación, con su score."""

    nombre: str
    pasa: bool
    valor: float
    detalle: str


class Publicador(Protocol):
    def gate(self, con: sqlite3.Connection, *, novel_id: str, version: int) -> list[VeredictoGate]:
        """Corre los validadores del gate sobre la versión que se va a publicar."""
        ...

    def publicar(
        self,
        con: sqlite3.Connection,
        *,
        novel_id: str,
        version: int,
        generacion_id: str,
        motivo: str | None,
    ) -> str:
        """Escribe la versión inmutable dentro de la transacción del llamante; devuelve su
        hash."""
        ...
