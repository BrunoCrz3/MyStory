"""Una novela ya planificada, para probar lo que viene después del planificador."""

from __future__ import annotations

from typing import Any

from app.process.planificar import planificar
from tests.conftest import Entorno
from tests.fixtures.briefs import brief_ejemplo
from tests.fixtures.esquemas import esquema_valido


async def novela_planificada(entorno: Entorno, brief: dict[str, Any] | None = None) -> str:
    brief = brief or brief_ejemplo()
    novela = await entorno.crear_novela(brief)
    entorno.modelo.encolar("planificador", esquema_valido(brief))
    await planificar(entorno.recursos, novel_id=novela, version=1)
    entorno.trazas.scores.clear()
    return novela
