"""Presupuesto en vuelo (RNF-10, RNF-13, P-36).

No es la ventana. La ventana la fija el proveedor y limita **una** peticion; esto
lo fija el autor y limita **cuantas caben a la vez**. Que hoy coincidan en la
misma cifra es deliberado y no las ata.

Tres reglas, y ninguna es de eficiencia:

- **Un trabajo no arranca sin presupuesto libre.** Espera antes de llamar, que es
  donde la espera no cuesta dinero. Sin esto, la rafaga de pasos de solo lectura
  de una escena se convierte en cascada: todos reciben 429 y todos reintentan a
  la vez.
- **Admision FIFO estricta.** Nadie adelanta a nadie aunque quepa. Es mas lento
  en conjunto, y a cambio el `redactor` --que pide la ventana entera-- no se
  queda esperando detras de una fila de criticos que nunca deja hueco bastante.
- **Un trabajo que no cabe entero falla al encolarse.** Esperar un hueco que no
  va a existir nunca no es esperar, es colgarse.

**Es un semaforo en proceso, no un recurso compartido.** Vive en memoria, no
persiste y no se coordina con nada externo. El punto ciego esta declarado en
P-36 y se asume: no sobrevive a un reinicio y no sabe de otras instancias.
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from app.commons.errores import PresupuestoExcedido


@dataclass
class _Turno:
    """Un trabajo en la cola de admision. La identidad la da el objeto."""

    tokens: int
    admitido: asyncio.Future[None] = field(repr=False)


class PoolEnVuelo:
    def __init__(self, total: int) -> None:
        self._total = total
        self._libre = total
        self._cola: deque[_Turno] = deque()

    @property
    def total(self) -> int:
        return self._total

    @property
    def libre(self) -> int:
        return self._libre

    @property
    def en_espera(self) -> int:
        return len(self._cola)

    @asynccontextmanager
    async def admitir(self, tokens: int) -> AsyncIterator[None]:
        """Reserva `tokens` del pool mientras dure el bloque.

        La estimacion de un trabajo es el tamano de su contexto ensamblado, que
        ya incluye `contexto.capas.margen` como reserva de respuesta: no se suma
        la respuesta dos veces.
        """
        if tokens > self._total:
            raise PresupuestoExcedido(
                f"el trabajo estima {tokens} tokens y el pool entero son {self._total}: "
                "nunca va a haber hueco, asi que no se encola"
            )

        turno = _Turno(tokens=tokens, admitido=asyncio.get_running_loop().create_future())
        self._cola.append(turno)
        self._repartir()
        try:
            await turno.admitido
        except BaseException:
            # Cancelado. Si ya se le habia dado el hueco hay que devolverlo; si
            # no, basta con sacarlo de la cola para que no bloquee a los de
            # detras. Un turno abandonado en cabeza seria un interbloqueo.
            if turno.admitido.done() and not turno.admitido.cancelled():
                self._liberar(tokens)
            elif turno in self._cola:
                self._cola.remove(turno)
                self._repartir()
            raise

        try:
            yield
        finally:
            self._liberar(tokens)

    def _liberar(self, tokens: int) -> None:
        self._libre += tokens
        self._repartir()

    def _repartir(self) -> None:
        """FIFO estricta: en cuanto el primero no cabe, se para.

        Seguir mirando la cola para colar a uno pequeno es justo lo que esta
        regla prohibe.
        """
        while self._cola:
            turno = self._cola[0]
            if turno.tokens > self._libre:
                return
            self._cola.popleft()
            self._libre -= turno.tokens
            if turno.admitido.done():
                # Cancelado entre medias: el hueco no llega a usarse.
                self._libre += turno.tokens
                continue
            turno.admitido.set_result(None)
