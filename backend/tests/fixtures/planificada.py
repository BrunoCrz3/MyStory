"""Una novela ya planificada, para probar lo que viene después del planificador."""

from __future__ import annotations

from typing import Any

from app.process import cola
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


async def encolar_inicial(entorno: Entorno, brief: dict[str, Any] | None = None) -> tuple[str, str]:
    """Crea la novela y encola su generación inicial; devuelve `novel_id` y `generacion_id`."""
    r = entorno.recursos
    novela = await entorno.crear_novela(brief or brief_ejemplo())
    generacion = await r.db.en_transaccion(
        lambda con: cola.encolar(
            con, r, novel_id=novela, tipo="inicial", accion="Planificar", version_objetivo=1
        )
    )
    return novela, str(generacion.generacion_id)


async def generar_entera(entorno: Entorno, brief: dict[str, Any] | None = None) -> tuple[str, str]:
    """Encola, reclama y ejecuta una generación inicial completa con el orquestador real."""
    novela, gid = await encolar_inicial(entorno, brief)
    assert await entorno.recursos.db.ejecutar(cola.reclamar) == gid
    await entorno.orquestador().ejecutar(gid)
    return novela, gid
