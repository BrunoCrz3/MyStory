"""Cada intento de un capítulo deja su informe de crítica con sus defectos y sus scores
(RF-OBS-03, RF-PROC-08: el informe del último intento de un capítulo agotado es consultable)."""

from __future__ import annotations

import pytest

from app.process.capitulo import ciclo_capitulo
from app.quality import service as quality
from app.quality.registro import validador
from tests.conftest import Entorno
from tests.fixtures.borradores import borrador
from tests.fixtures.planificada import novela_planificada

VALIDADORES_DEL_CICLO = ["schema_valido", "palabras_prohibidas", "longitud", "nombres_exactos"]


def _informes(entorno: Entorno, novela: str, capitulo_id: str) -> list[quality.InformeCritica]:
    return entorno.recursos.db.ejecutar_sync(
        lambda con: quality.informes_de_capitulo(con, novel_id=novela, capitulo_id=capitulo_id)
    )


@pytest.mark.anyio
async def test_cada_intento_deja_su_informe_con_defectos_y_scores(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    entorno.modelo.encolar("redactor", borrador(500), borrador())
    r = await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=1)
    assert r.accion == "aceptar"

    primero, segundo = _informes(entorno, novela, r.capitulo_id)
    assert (primero.intento, primero.decision) == (0, "devolver")
    assert (segundo.intento, segundo.decision) == (1, "aceptar")
    assert [d.dimension for d in primero.defectos] == ["longitud"]
    assert "500 palabras" in primero.defectos[0].descripcion
    assert segundo.defectos == []
    for informe in (primero, segundo):
        assert [s.validador for s in informe.scores] == VALIDADORES_DEL_CICLO
    assert [s.pasa for s in primero.scores] == [True, True, False, True]
    assert all(s.pasa for s in segundo.scores)
    # Un score por validador ejecutado, igual en la base que en la traza (RF-OBS-03).
    assert len(entorno.consultar("SELECT id FROM score WHERE novel_id = ?", novela)) == 8
    assert len(entorno.trazas.scores) == 8


@pytest.mark.anyio
async def test_el_informe_del_ultimo_intento_de_un_capitulo_agotado_es_consultable(
    entorno: Entorno,
) -> None:
    novela = await novela_planificada(entorno)
    limite = entorno.recursos.config.umbrales.orquestacion.max_intentos_capitulo
    entorno.modelo.encolar("redactor", *[borrador(500)] * (limite + 1))
    r = await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=1)
    assert r.accion == "agotar"

    informes = _informes(entorno, novela, r.capitulo_id)
    assert [i.intento for i in informes] == list(range(limite + 1))
    ultimo = entorno.recursos.db.ejecutar_sync(
        lambda con: quality.ultimo_informe(con, novel_id=novela, capitulo_id=r.capitulo_id)
    )
    assert ultimo == informes[-1]
    assert ultimo.decision == "agotar"
    assert [d.dimension for d in ultimo.defectos] == ["longitud"]


@pytest.mark.anyio
async def test_un_borrador_sin_schema_deja_informe_sin_el_hook_de_capitulo(
    entorno: Entorno,
) -> None:
    novela = await novela_planificada(entorno)
    entorno.modelo.encolar("redactor", {"titulo": "sin texto"}, borrador())
    r = await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=1)
    primero = _informes(entorno, novela, r.capitulo_id)[0]
    assert [s.validador for s in primero.scores] == ["schema_valido"]
    assert primero.defectos[0].dimension == validador("schema_valido").nombre


def test_un_capitulo_sin_intentos_no_tiene_informe(entorno: Entorno) -> None:
    db = entorno.recursos.db
    assert (
        db.ejecutar_sync(lambda con: quality.ultimo_informe(con, novel_id="n", capitulo_id="c"))
        is None
    )
    assert (
        db.ejecutar_sync(
            lambda con: quality.informes_de_capitulo(con, novel_id="n", capitulo_id="c")
        )
        == []
    )
