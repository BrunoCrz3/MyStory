"""El único camino al modelo (RNF-08, RF-CTX-02).

`LlamadorModelo.llamar()` cuenta la petición, comprueba que cabe en `contexto.total`, pide
hueco en el pool, abre el span del rol y llama. Ningún módulo fuera de `commons/llm/` habla
con el `ClienteModelo` directamente: lo comprueba la prueba de arquitectura.
"""

from __future__ import annotations

import contextvars
import random
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import anyio

from app.commons.config import Config
from app.commons.llm.pool import PoolEnVuelo
from app.commons.llm.protocolo import (
    ClienteModelo,
    ErrorModelo,
    FalloInfraestructura,
    Peticion,
    Recuento,
    Respuesta,
)
from app.commons.observabilidad.protocolo import Trazador


@dataclass
class Consumo:
    """Tokens, coste y llamadas de un trabajo, acumulados por cada llamada que se hace dentro
    de `acumular_en()` (RF-OBS-04). Va en una variable de contexto: dos novelas que generan
    a la vez no se mezclan las cuentas."""

    tokens_entrada: int = 0
    tokens_salida: int = 0
    coste_usd: float = 0.0
    llamadas: int = 0
    reintentos_infra: int = 0

    @property
    def tokens(self) -> int:
        return self.tokens_entrada + self.tokens_salida


_consumo: contextvars.ContextVar[Consumo | None] = contextvars.ContextVar("consumo", default=None)


@contextmanager
def acumular_en(consumo: Consumo) -> Iterator[Consumo]:
    ficha = _consumo.set(consumo)
    try:
        yield consumo
    finally:
        _consumo.reset(ficha)


class ContextoNoCabe(ErrorModelo):
    """El ensamblado supera `contexto.total` después de degradar. Falla en voz alta, sin
    llamar al modelo y sin truncar."""


Dormir = Callable[[float], Awaitable[None]]


class LlamadorModelo:
    def __init__(
        self,
        config: Config,
        cliente: ClienteModelo,
        pool: PoolEnVuelo,
        trazador: Trazador,
        *,
        dormir: Dormir = anyio.sleep,
        azar: Callable[[], float] = random.random,
    ) -> None:
        self.config = config
        self.cliente = cliente
        self.pool = pool
        self.trazador = trazador
        self._dormir = dormir
        self._azar = azar

    async def _con_reintentos(self, llamada: Callable[[], Awaitable[Recuento | Respuesta]]) -> Any:
        """Reintenta los fallos de infraestructura con retroceso exponencial y jitter
        (RF-PROC-09). Tiene su propio contador y no gasta intentos del capítulo (TO-014);
        agotado, el fallo sube y la generación se detiene e informa."""
        orq = self.config.umbrales.orquestacion
        b = orq.backoff
        for intento in range(orq.max_intentos_trabajo + 1):
            try:
                return await llamada()
            except FalloInfraestructura:
                if intento == orq.max_intentos_trabajo:
                    raise
                espera = b.base_segundos * b.factor**intento
                if b.jitter:
                    espera *= 1 + self._azar()
                consumo = _consumo.get()
                if consumo is not None:
                    consumo.reintentos_infra += 1
                await self._dormir(espera)
        raise AssertionError("inalcanzable")

    async def contar(self, peticion: Peticion) -> int:
        """Tokens de entrada de una petición, con el contador del proveedor."""
        recuento: Recuento = await self._con_reintentos(
            lambda: self.cliente.contar_tokens(peticion)
        )
        return recuento.tokens_entrada

    async def llamar(self, peticion: Peticion) -> Respuesta:
        recuento: Recuento = await self._con_reintentos(
            lambda: self.cliente.contar_tokens(peticion)
        )
        total = self.config.umbrales.contexto.total
        if recuento.estimacion > total:
            raise ContextoNoCabe(
                f"{peticion.rol}: la petición ocupa {recuento.tokens_entrada} tokens más "
                f"{recuento.max_tokens} de salida y el límite por petición es {total}"
            )

        async def generar() -> Respuesta:
            async with self.pool.reservar(recuento.estimacion):
                with self.trazador.generacion(peticion) as observacion:
                    try:
                        respuesta = await self.cliente.generar(peticion, recuento)
                    except BaseException as e:
                        observacion.error(e)
                        raise
                    observacion.registrar(respuesta)
                    return respuesta

        respuesta: Respuesta = await self._con_reintentos(generar)
        consumo = _consumo.get()
        if consumo is not None:
            consumo.tokens_entrada += respuesta.tokens_entrada
            consumo.tokens_salida += respuesta.tokens_salida
            consumo.coste_usd += respuesta.coste_usd
            consumo.llamadas += 1
        return respuesta
