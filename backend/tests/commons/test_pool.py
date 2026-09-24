"""Pool de tokens en vuelo con admisión FIFO estricta (RNF-02, RNF-03)."""

from __future__ import annotations

import asyncio

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.commons.errores import TrabajoNoCabeEnPool
from app.commons.llm.pool import PoolEnVuelo


@given(
    total=st.integers(min_value=10, max_value=200),
    pesos=st.lists(st.integers(min_value=1, max_value=10), min_size=1, max_size=40),
    esperas=st.lists(st.integers(min_value=0, max_value=3), min_size=40, max_size=40),
)
@settings(max_examples=60, deadline=None)
def test_la_suma_en_vuelo_nunca_supera_el_total(
    total: int, pesos: list[int], esperas: list[int]
) -> None:
    async def escenario() -> None:
        pool = PoolEnVuelo(total)
        maximo = 0

        async def llamada(peso: int, espera: int) -> None:
            nonlocal maximo
            async with pool.reservar(peso):
                maximo = max(maximo, pool.ocupado)
                assert pool.ocupado <= total
                for _ in range(espera):
                    await asyncio.sleep(0)

        await asyncio.gather(*(llamada(p, esperas[i]) for i, p in enumerate(pesos)))
        assert maximo <= total
        assert pool.ocupado == 0
        assert pool.en_espera == 0

    asyncio.run(escenario())


def test_fifo_estricto_nadie_adelanta() -> None:
    async def escenario() -> list[str]:
        pool = PoolEnVuelo(10)
        orden: list[str] = []
        suelta_a = asyncio.Event()

        async def a() -> None:
            async with pool.reservar(8):
                orden.append("a")
                await suelta_a.wait()

        async def b() -> None:
            async with pool.reservar(5):
                orden.append("b")

        async def c() -> None:
            async with pool.reservar(2):
                orden.append("c")

        ta = asyncio.create_task(a())
        await asyncio.sleep(0)
        tb = asyncio.create_task(b())
        await asyncio.sleep(0)
        tc = asyncio.create_task(c())
        await asyncio.sleep(0.01)
        # `c` cabría (8 + 2 <= 10), pero `b` llegó antes y está esperando.
        assert orden == ["a"]
        suelta_a.set()
        await asyncio.gather(ta, tb, tc)
        return orden

    assert asyncio.run(escenario()) == ["a", "b", "c"]


def test_una_estimacion_mayor_que_el_total_falla_sin_esperar() -> None:
    async def escenario() -> None:
        pool = PoolEnVuelo(100)
        with pytest.raises(TrabajoNoCabeEnPool):
            async with pool.reservar(101):
                pass
        assert pool.en_espera == 0

    asyncio.run(escenario())


def test_el_peso_se_libera_si_la_llamada_lanza() -> None:
    async def escenario() -> None:
        pool = PoolEnVuelo(10)
        with pytest.raises(RuntimeError):
            async with pool.reservar(7):
                raise RuntimeError("falla la llamada")
        assert pool.ocupado == 0

    asyncio.run(escenario())


def test_cancelar_mientras_espera_no_bloquea_la_cola() -> None:
    async def escenario() -> None:
        pool = PoolEnVuelo(10)
        suelta = asyncio.Event()
        hechos: list[str] = []

        async def ocupa() -> None:
            async with pool.reservar(10):
                await suelta.wait()

        async def espera(nombre: str, peso: int) -> None:
            async with pool.reservar(peso):
                hechos.append(nombre)

        t1 = asyncio.create_task(ocupa())
        await asyncio.sleep(0)
        t2 = asyncio.create_task(espera("cancelada", 6))
        await asyncio.sleep(0)
        t3 = asyncio.create_task(espera("siguiente", 6))
        await asyncio.sleep(0)
        t2.cancel()
        await asyncio.sleep(0)
        suelta.set()
        await asyncio.gather(t1, t3)
        with pytest.raises(asyncio.CancelledError):
            await t2
        assert hechos == ["siguiente"]
        assert pool.ocupado == 0
        assert pool.en_espera == 0

    asyncio.run(escenario())
