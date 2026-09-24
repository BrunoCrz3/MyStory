"""El worker único en proceso (RF-PROC-03, TO-030).

Arranca con el `lifespan` y se para con él. Reclama trabajos de la tabla con una
actualización condicional atómica y los ejecuta de uno en uno. No sondea con una espera fija:
duerme hasta que alguien encola y le avisa, y al arrancar mira si ya había pendientes. Lo
que estaba en curso cuando el proceso anterior murió vuelve antes a la cola (RF-PROC-06).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from app.commons.recursos import Recursos
from app.process import cola
from app.process.orquestador import Orquestador
from app.process.service import Publicador

_log = logging.getLogger("storymaker.worker")


class Worker:
    def __init__(self, r: Recursos, publicador: Publicador) -> None:
        self.r = r
        self.orquestador = Orquestador(r, publicador)
        self._hay_trabajo = asyncio.Event()
        self._tarea: asyncio.Task[None] | None = None
        self._parar = False

    @property
    def vivo(self) -> bool:
        return self._tarea is not None and not self._tarea.done()

    def avisar(self) -> None:
        self._hay_trabajo.set()

    def arrancar(self) -> None:
        self._tarea = asyncio.create_task(self._bucle(), name="worker-storymaker")

    async def parar(self) -> None:
        self._parar = True
        self._hay_trabajo.set()
        if self._tarea is not None:
            self._tarea.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._tarea

    async def _bucle(self) -> None:
        huerfanos = await self.r.db.ejecutar(cola.devolver_huerfanos)
        if huerfanos:
            _log.warning("se retoman %d generaciones interrumpidas", len(huerfanos))
        while not self._parar:
            self._hay_trabajo.clear()
            generacion_id = await self.r.db.ejecutar(cola.reclamar)
            if generacion_id is None:
                await self._hay_trabajo.wait()
                continue
            try:
                await self.orquestador.ejecutar(generacion_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                # La red de seguridad: el orquestador ya registra sus fallos de dominio. Esto
                # es un fallo no previsto, y el trabajo queda en curso para que la reanudación
                # lo retome en vez de perderse.
                _log.exception("fallo no previsto en la generación %s", generacion_id)
