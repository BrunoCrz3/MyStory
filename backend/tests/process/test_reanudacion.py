"""Checkpoint y reanudación (RF-PROC-06, TO-023).

Un corte se simula con una excepción no prevista dentro de una llamada al modelo: el proceso
deja el trabajo `en-curso` y el capítulo a medias, que es lo que ve el siguiente arranque.
"""

from __future__ import annotations

import asyncio
import contextlib
import tempfile
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from app.commons.config import Rol
from app.commons.llm import Peticion
from app.main import crear_app
from app.process import cola
from app.process.orquestador import Orquestador
from tests.conftest import Entorno, crear_entorno
from tests.dobles.guiones import guion_completo
from tests.fixtures.briefs import brief_ejemplo
from tests.process.test_orquestador import esperar

TOTAL = 10


class Corte(Exception):
    """El proceso muere a mitad de una llamada: nadie la captura como fallo de dominio."""


def cortar_en(entorno: Entorno, rol: Rol, llamada: int) -> None:
    """La llamada número `llamada` del rol muere; las demás responden con el guion."""
    original: Callable[[Peticion], Any] = entorno.modelo.por_defecto[rol]
    vistas = 0

    def guion(p: Peticion) -> Any:
        nonlocal vistas
        vistas += 1
        if vistas == llamada:
            raise Corte(f"{rol} {llamada}")
        return original(p)

    entorno.modelo.por_defecto[rol] = guion


async def lanzar(entorno: Entorno) -> tuple[str, str]:
    r = entorno.recursos
    novela = await entorno.crear_novela(brief_ejemplo())
    generacion = await r.db.en_transaccion(
        lambda con: cola.encolar(
            con, r, novel_id=novela, tipo="inicial", accion="Planificar", version_objetivo=1
        )
    )
    return novela, str(generacion.generacion_id)


async def ejecutar_hasta_el_corte(entorno: Entorno, gid: str) -> None:
    assert await entorno.recursos.db.ejecutar(cola.reclamar) == gid
    with pytest.raises(Corte):
        await Orquestador(entorno.recursos).ejecutar(gid)


async def reanudar(entorno: Entorno, gid: str) -> None:
    """Lo que hace un arranque: devolver huérfanos, reclamar y ejecutar."""
    r = entorno.recursos
    assert await r.db.ejecutar(cola.devolver_huerfanos) == [gid]
    assert await r.db.ejecutar(cola.reclamar) == gid
    await Orquestador(r).ejecutar(gid)


def capitulos(entorno: Entorno, novela: str) -> dict[int, tuple[str, str]]:
    filas = entorno.consultar(
        "SELECT numero, id, estado FROM capitulo WHERE novel_id = ? AND version = 1", novela
    )
    return {f["numero"]: (f["id"], f["estado"]) for f in filas}


def aceptados(entorno: Entorno, novela: str) -> list[int]:
    return sorted(n for n, (_, e) in capitulos(entorno, novela).items() if e == "Aceptado")


def checkpoint(entorno: Entorno, gid: str) -> int | None:
    filas = entorno.consultar("SELECT ultimo_capitulo FROM checkpoint WHERE generacion_id = ?", gid)
    return filas[0]["ultimo_capitulo"] if filas else None


@pytest.mark.anyio
async def test_el_capitulo_a_medias_vuelve_a_pendiente_y_sigue_por_el(entorno: Entorno) -> None:
    guion_completo(entorno.modelo)
    cortar_en(entorno, "redactor", 5)
    novela, gid = await lanzar(entorno)
    await ejecutar_hasta_el_corte(entorno, gid)

    antes = capitulos(entorno, novela)
    assert aceptados(entorno, novela) == [1, 2, 3, 4]
    assert antes[5][1] == "Escribiendo"
    assert checkpoint(entorno, gid) == 4

    normalizados = await Orquestador(entorno.recursos).estado_inicial(novela, 1)
    assert normalizados == [5]
    assert capitulos(entorno, novela)[5][1] == "Pendiente"
    assert checkpoint(entorno, gid) == 4

    redactados = entorno.modelo.llamadas["redactor"]
    await reanudar(entorno, gid)
    despues = capitulos(entorno, novela)
    assert aceptados(entorno, novela) == list(range(1, TOTAL + 1))
    assert all(despues[n][0] == antes[n][0] for n in range(1, 5))
    assert entorno.modelo.llamadas["redactor"] - redactados == TOTAL - 4
    assert checkpoint(entorno, gid) == TOTAL
    assert entorno.consultar("SELECT estado FROM obra WHERE novel_id = ?", novela)[0][0] == (
        "Validando"
    )


@pytest.mark.anyio
@pytest.mark.parametrize("estado", ["Escribiendo", "Validando", "Reescribiendo"])
async def test_estado_inicial_normaliza_todo_estado_intermedio(
    entorno: Entorno, estado: str
) -> None:
    guion_completo(entorno.modelo)
    cortar_en(entorno, "redactor", 3)
    novela, gid = await lanzar(entorno)
    await ejecutar_hasta_el_corte(entorno, gid)
    entorno.recursos.db.ejecutar_sync(
        lambda con: con.execute(
            "UPDATE capitulo SET estado = ?, intentos = 1"
            " WHERE novel_id = ? AND numero = 3 AND version = 1",
            (estado, novela),
        )
    )
    assert await Orquestador(entorno.recursos).estado_inicial(novela, 1) == [3]
    fila = entorno.consultar(
        "SELECT estado, intentos FROM capitulo WHERE novel_id = ? AND numero = 3", novela
    )[0]
    # La reanudación no regala intentos: un proceso que cae una y otra vez sigue acotado.
    assert (fila["estado"], fila["intentos"]) == ("Pendiente", 1)
    assert aceptados(entorno, novela) == [1, 2]


@pytest.mark.anyio
async def test_un_corte_entre_planificar_y_fijar_el_esquema_no_replanifica(
    entorno: Entorno,
) -> None:
    guion_completo(entorno.modelo)
    cortar_en(entorno, "redactor", 1)
    novela, gid = await lanzar(entorno)
    await ejecutar_hasta_el_corte(entorno, gid)
    # Como si el proceso hubiera muerto justo después de guardar el esquema.
    entorno.recursos.db.ejecutar_sync(
        lambda con: con.execute(
            "UPDATE obra SET estado = 'Planificando' WHERE novel_id = ?", (novela,)
        )
    )
    await reanudar(entorno, gid)
    assert entorno.modelo.llamadas["planificador"] == 1
    assert aceptados(entorno, novela) == list(range(1, TOTAL + 1))


def _corte() -> st.SearchStrategy[tuple[Rol, int]]:
    return st.tuples(st.sampled_from(list[Rol](["redactor", "extractor"])), st.integers(1, TOTAL))


@settings(max_examples=8)
@given(cortes=st.lists(_corte(), min_size=1, max_size=2))
def test_propiedad_los_aceptados_son_un_prefijo_y_ninguno_se_acepta_dos_veces(
    cortes: list[tuple[Rol, int]],
) -> None:
    async def caso(entorno: Entorno) -> None:
        guion_completo(entorno.modelo)
        novela, gid = await lanzar(entorno)
        ids: dict[int, str] = {}
        assert await entorno.recursos.db.ejecutar(cola.reclamar) == gid
        for rol, n in cortes:
            # La n-ésima llamada del rol desde este arranque; si no llega, no hay corte.
            base = dict(entorno.modelo.por_defecto)
            cortar_en(entorno, rol, n)
            with contextlib.suppress(Corte):
                await Orquestador(entorno.recursos).ejecutar(gid)
            entorno.modelo.por_defecto.update(base)

            hechos = aceptados(entorno, novela)
            assert hechos == list(range(1, len(hechos) + 1))
            if hechos:
                assert checkpoint(entorno, gid) == len(hechos)
            actuales = capitulos(entorno, novela)
            for numero, cid in ids.items():
                assert actuales[numero][0] == cid
            ids = {numero: actuales[numero][0] for numero in hechos}
            if not await entorno.recursos.db.ejecutar(cola.devolver_huerfanos):
                break
            assert await entorno.recursos.db.ejecutar(cola.reclamar) == gid

        if entorno.consultar("SELECT estado_cola FROM trabajo WHERE id = ?", gid)[0][0] != (
            "terminado"
        ):
            await Orquestador(entorno.recursos).ejecutar(gid)
        assert aceptados(entorno, novela) == list(range(1, TOTAL + 1))
        # Un snapshot por capítulo aceptado: consolidar no corrió dos veces para ninguno.
        snapshots = entorno.consultar(
            "SELECT c.numero FROM snapshot s JOIN capitulo c ON c.id = s.capitulo_id"
            " WHERE s.novel_id = ?",
            novela,
        )
        assert Counter(f["numero"] for f in snapshots) == Counter(range(1, TOTAL + 1))
        assert (
            entorno.consultar("SELECT count(*) FROM trabajo WHERE novel_id = ?", novela)[0][0] == 1
        )

    with tempfile.TemporaryDirectory() as carpeta:
        asyncio.run(caso(crear_entorno(Path(carpeta) / "prop.db")))


def test_un_trabajo_huerfano_al_arrancar_se_retoma_sin_duplicarse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ruta = tmp_path / "huerfano.db"
    entorno = crear_entorno(ruta)
    guion_completo(entorno.modelo)
    cortar_en(entorno, "redactor", 6)

    async def primer_proceso() -> tuple[str, str]:
        novela, gid = await lanzar(entorno)
        await ejecutar_hasta_el_corte(entorno, gid)
        return novela, gid

    novela, gid = asyncio.run(primer_proceso())
    antes = capitulos(entorno, novela)
    assert entorno.consultar("SELECT estado_cola FROM trabajo WHERE id = ?", gid)[0][0] == (
        "en-curso"
    )

    monkeypatch.setenv("STORYMAKER_DB_PATH", str(ruta))
    guion_completo(entorno.modelo)
    app = crear_app(entorno.recursos.config, cliente_modelo=entorno.modelo, trazador=entorno.trazas)
    with TestClient(app) as cliente:
        g = esperar(cliente, novela, gid, lambda g: g["capitulos_aceptados"] == TOTAL)
        generaciones = cliente.get(f"/novelas/{novela}/generaciones").json()
    assert g["checkpoint"] == TOTAL
    assert [x["generacion_id"] for x in generaciones] == [gid]
    despues = capitulos(entorno, novela)
    assert all(despues[n][0] == antes[n][0] for n in range(1, 6))
