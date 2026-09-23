"""H6 · prueba 8 — P-36, RNF-10, RNF-13.

Tres afirmaciones sobre el pool en vuelo, y cada una protege de un fallo
distinto:

- **Un trabajo no arranca sin presupuesto libre.** Sin control de admision, la
  rafaga de pasos de una escena se convierte en cascada de 429 y reintentos
  sincronizados.
- **La admision es FIFO estricta.** Nadie adelanta a nadie aunque quepa. Es mas
  lento en conjunto, y a cambio el redactor --que pide la ventana entera-- no se
  queda esperando detras de una fila de criticos.
- **Un trabajo que no cabe entero falla al encolarse.** Esperar un hueco que no
  va a existir nunca no es esperar, es colgarse.

El punto ciego esta declarado y se asume: el pool es un semaforo en memoria, no
sobrevive a un reinicio y no sabe de otras instancias. Y el orden se comprueba
sobre la cola, no sobre el proveedor: dos trabajos admitidos en orden pueden
llegar al modelo al reves.
"""

from __future__ import annotations

import asyncio

import pytest

from app.commons.errores import PresupuestoExcedido
from app.commons.tokens.en_vuelo import PoolEnVuelo


def test_un_trabajo_no_arranca_sin_presupuesto_en_vuelo_libre() -> None:
    dentro: list[str] = []

    async def escenario() -> None:
        pool = PoolEnVuelo(total=100)

        async def trabajo(nombre: str, tokens: int, espera: float) -> None:
            async with pool.admitir(tokens):
                dentro.append(nombre)
                await asyncio.sleep(espera)

        grande = asyncio.create_task(trabajo("grande", 80, 0.05))
        await asyncio.sleep(0)
        segundo = asyncio.create_task(trabajo("segundo", 80, 0))
        await asyncio.sleep(0.01)
        assert dentro == ["grande"], "el segundo entro sin que hubiera hueco"
        assert pool.libre == 20
        await asyncio.gather(grande, segundo)

    asyncio.run(escenario())
    assert dentro == ["grande", "segundo"]


def test_la_admision_es_fifo_y_nadie_adelanta() -> None:
    """El pequeno cabe mientras el grande espera, y aun asi no se cuela.

    Es la propiedad cara del pool y la que se cae sola si alguien «optimiza»:
    dejar pasar al que cabe es exactamente lo que deja al redactor sin turno.
    """
    orden: list[str] = []

    async def escenario() -> None:
        pool = PoolEnVuelo(total=100)

        async def trabajo(nombre: str, tokens: int) -> None:
            async with pool.admitir(tokens):
                orden.append(nombre)
                await asyncio.sleep(0.01)

        ocupante = asyncio.create_task(trabajo("ocupante", 60))
        await asyncio.sleep(0)
        grande = asyncio.create_task(trabajo("grande", 90))
        await asyncio.sleep(0)
        pequeno = asyncio.create_task(trabajo("pequeno", 10))
        await asyncio.gather(ocupante, grande, pequeno)

    asyncio.run(escenario())
    assert orden == ["ocupante", "grande", "pequeno"]


def test_un_trabajo_que_no_cabe_entero_falla_al_encolarse() -> None:
    async def escenario() -> None:
        pool = PoolEnVuelo(total=100)
        with pytest.raises(PresupuestoExcedido):
            async with pool.admitir(101):
                raise AssertionError("no deberia haber entrado")

    asyncio.run(escenario())


def test_el_presupuesto_vuelve_al_pool_aunque_el_trabajo_falle() -> None:
    """Un fallo del proveedor no puede dejar el pool encogido para siempre."""

    async def escenario() -> None:
        pool = PoolEnVuelo(total=100)
        with pytest.raises(ZeroDivisionError):
            async with pool.admitir(100):
                raise ZeroDivisionError
        assert pool.libre == 100
        async with pool.admitir(100):
            assert pool.libre == 0

    asyncio.run(escenario())


def test_un_trabajo_cancelado_en_la_cola_no_bloquea_a_los_de_detras() -> None:
    """Un turno abandonado en cabeza seria un interbloqueo, no una espera."""
    entraron: list[str] = []

    async def escenario() -> None:
        pool = PoolEnVuelo(total=100)

        async def trabajo(nombre: str, tokens: int, espera: float) -> None:
            async with pool.admitir(tokens):
                entraron.append(nombre)
                await asyncio.sleep(espera)

        ocupante = asyncio.create_task(trabajo("ocupante", 100, 0.02))
        await asyncio.sleep(0)
        abandona = asyncio.create_task(trabajo("abandona", 100, 0))
        await asyncio.sleep(0)
        detras = asyncio.create_task(trabajo("detras", 100, 0))
        await asyncio.sleep(0)
        abandona.cancel()
        await asyncio.gather(ocupante, detras)
        assert pool.libre == 100

    asyncio.run(escenario())
    assert entraron == ["ocupante", "detras"]
