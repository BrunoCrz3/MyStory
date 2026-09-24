"""`render_visual`: el gate pinta la versión candidata en la página `lectura` (TO-026, TO-045).

Aquí vive el puerto. La implementación con el servidor Playwright MCP llega en el P47b; hasta
entonces, y después siempre que `PLAYWRIGHT_MCP_URL` no esté configurada, la de producción es
`SinNavegador`, que falla con el motivo: sin validación visual ninguna versión se publica
(RNF-19, A-114).
"""

from __future__ import annotations

from typing import Protocol

from app.process.service import VeredictoGate

NOMBRE = "render_visual"


class RenderVisual(Protocol):
    async def __call__(self, *, novel_id: str, version: int) -> VeredictoGate: ...


class SinNavegador:
    """Sin servidor MCP no hay render que afirmar: el validador falla y lo dice."""

    async def __call__(self, *, novel_id: str, version: int) -> VeredictoGate:
        return VeredictoGate(
            nombre=NOMBRE,
            pasa=False,
            valor=0.0,
            detalle=(
                f"no hay servidor Playwright MCP configurado (PLAYWRIGHT_MCP_URL): la versión "
                f"{version} no se puede pintar y, sin validación visual, no se publica"
            ),
        )
