"""Vigencia por versión del evento (TO-066, RF-LEAN-07).

Una regeneración cierra los eventos del capítulo sustituido en la versión nueva y la
anterior conserva los suyos; una regeneración rechazada deja sus eventos con intervalo vacío
y reabre los que había cerrado (TO-062). Se reutilizan las novelas de TO-062.
"""

from __future__ import annotations

from functools import partial

import pytest

from app.novel import service as novel
from app.process import cola
from tests.canon.test_hechos_por_version import _extraer
from tests.conftest import Entorno
from tests.dobles.guiones import redactar
from tests.process.test_regeneracion_fallida import _confirmar, _regenerar_fallando_el_7
from tests.versioning.test_confirmar import _publicada


def _por_vinculo(e: Entorno, novela: str, version: int) -> set[str]:
    return {
        str(f["evento_id"])
        for f in e.consultar(
            "SELECT ec.evento_id FROM version_capitulo vc JOIN evento_capitulo ec"
            " ON ec.capitulo_id = vc.capitulo_id WHERE vc.novel_id = ? AND vc.version = ?",
            novela,
            version,
        )
    }


async def _vigentes(e: Entorno, novela: str, version: int) -> set[str]:
    eventos = await e.recursos.db.ejecutar(
        lambda con: novel.eventos_de_version(con, novel_id=novela, version=version)
    )
    return {ev.evento_id for ev in eventos}


@pytest.mark.anyio
async def test_una_version_nueva_lleva_los_eventos_con_su_version(entorno: Entorno) -> None:
    novela = await _publicada(entorno)
    filas = entorno.consultar("SELECT version_desde FROM evento WHERE novel_id = ?", novela)
    assert filas and {f["version_desde"] for f in filas} == {1}
    assert await _vigentes(entorno, novela, 1) == _por_vinculo(entorno, novela, 1)


@pytest.mark.anyio
async def test_una_regeneracion_publicada_cierra_los_eventos_sustituidos(
    entorno: Entorno,
) -> None:
    novela = await _publicada(entorno)
    entorno.modelo.por_defecto["extractor"] = partial(_extraer, n=102)
    g = await _confirmar(entorno, novela)
    await entorno.orquestador().ejecutar(str(g.generacion_id))
    [dirigida] = [
        x for x in await cola.listar_generaciones(entorno.recursos, novela) if x.tipo == "dirigida"
    ]
    assert dirigida.version_resultante == 2, dirigida

    for version in (1, 2):
        assert await _vigentes(entorno, novela, version) == _por_vinculo(entorno, novela, version)
    assert await _vigentes(entorno, novela, 1) != await _vigentes(entorno, novela, 2)


@pytest.mark.anyio
async def test_una_regeneracion_rechazada_no_deja_eventos_vigentes(entorno: Entorno) -> None:
    novela, g, _ = await _regenerar_fallando_el_7(entorno)
    assert g.estado == "Detenida", g
    antes = await _vigentes(entorno, novela, 1)
    assert antes == _por_vinculo(entorno, novela, 1)
    # Ningún evento que escribió la candidata sigue vigente en versión alguna.
    [n] = entorno.consultar(
        "SELECT count(*) AS n FROM evento WHERE novel_id = ? AND version_desde = 2"
        " AND (version_hasta IS NULL OR version_hasta > 2)",
        novela,
    )
    assert n["n"] == 0
    # Y lo que la candidata había cerrado vuelve a estar abierto: la siguiente parte de la 1.
    entorno.modelo.por_defecto["redactor"] = redactar
    entorno.modelo.por_defecto["extractor"] = partial(_extraer, n=103)
    g3 = await _confirmar(entorno, novela)
    await entorno.orquestador().ejecutar(str(g3.generacion_id))
    assert await _vigentes(entorno, novela, 3) == _por_vinculo(entorno, novela, 3)
    assert await _vigentes(entorno, novela, 1) == antes
