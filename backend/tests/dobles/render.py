"""Doble del puerto `RenderVisual` (P47a, TO-045): sin navegador ni servidor MCP.

Devuelve el veredicto que se le pida y guarda cada versión que se le pasó. `al_pintar`, si se
da, corre en el momento del render: las pruebas lo usan para mirar la versión **mientras** es
candidata, que es lo que el render real pinta.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from app.process.service import VeredictoGate


@dataclass
class RenderGuionizado:
    pasa: bool = True
    detalle: str = "la lectura pinta la versión candidata"
    al_pintar: Callable[[str, int], Awaitable[None]] | None = None
    pintadas: list[tuple[str, int]] = field(default_factory=list)

    async def __call__(self, *, novel_id: str, version: int) -> VeredictoGate:
        self.pintadas.append((novel_id, version))
        if self.al_pintar is not None:
            await self.al_pintar(novel_id, version)
        return VeredictoGate(
            nombre="render_visual",
            pasa=self.pasa,
            valor=1.0 if self.pasa else 0.0,
            detalle=self.detalle if self.pasa else "falta el selector portada-dedicatoria",
        )
