"""Pool de tokens en vuelo: un semáforo por peso, en proceso y compartido por toda la
instancia (RNF-02).

**Es un guardarraíl, no un planificador.** La admisión es FIFO estricta: una petición
espera aunque quepa si hay otra delante, para que el `writer`, que pide más, no se quede
detrás de una fila de llamadas cortas que nunca dejan hueco (`architecture.md`
§ Presupuesto de tokens concurrentes). Una estimación mayor que el total falla al pedirla:
esperar un hueco que no va a existir es colgarse (RNF-03).
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from app.commons.errores import TrabajoNoCabeEnPool


@dataclass
class _Turno:
    peso: int
    concedido: asyncio.Event = field(default_factory=asyncio.Event)


class PoolEnVuelo:
    def __init__(self, total: int) -> None:
        if total <= 0:
            raise ValueError("el presupuesto en vuelo tiene que ser positivo")
        self.total = total
        self.ocupado = 0
        self._cola: deque[_Turno] = deque()

    @property
    def en_espera(self) -> int:
        return len(self._cola)

    @property
    def libre(self) -> int:
        return self.total - self.ocupado

    def comprobar(self, peso: int) -> None:
        """Lanza si `peso` no cabrá nunca. Sirve para rechazar un trabajo al encolarlo."""
        if peso > self.total:
            raise TrabajoNoCabeEnPool(
                f"la llamada estima {peso} tokens y el presupuesto en vuelo total es "
                f"{self.total}: es un error de diseño del ensamblado, no una espera"
            )

    @asynccontextmanager
    async def reservar(self, peso: int) -> AsyncIterator[None]:
        self.comprobar(peso)
        await self._entrar(peso)
        try:
            yield
        finally:
            self.ocupado -= peso
            self._despachar()

    async def _entrar(self, peso: int) -> None:
        if not self._cola and self.ocupado + peso <= self.total:
            self.ocupado += peso
            return
        turno = _Turno(peso)
        self._cola.append(turno)
        try:
            await turno.concedido.wait()
        except asyncio.CancelledError:
            if turno.concedido.is_set():
                # Se le concedió justo antes de cancelarse: devuelve lo que se le dio.
                self.ocupado -= peso
            else:
                self._cola.remove(turno)
            self._despachar()
            raise

    def _despachar(self) -> None:
        while self._cola and self.ocupado + self._cola[0].peso <= self.total:
            turno = self._cola.popleft()
            self.ocupado += turno.peso
            turno.concedido.set()
