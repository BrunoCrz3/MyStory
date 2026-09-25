"""Lean en el gate de publicación (RF-LEAN-03, RF-LEAN-05, P-64, P-82, regla 16).

`lake build` real: la candidata con una violación no se publica y el fallo vuelve al editor
por `GateEnRojo`; la limpia se publica. En una regeneración, la versión publicada no cambia.
"""

from __future__ import annotations

import dataclasses
from functools import partial
from typing import Any

import pytest

from app.commons.llm import Peticion
from app.process import cola
from tests.canon.test_hechos_por_version import _extraer
from tests.conftest import Entorno
from tests.dobles.guiones import guion_completo
from tests.fixtures.briefs import brief_ejemplo
from tests.process.test_regeneracion_fallida import _confirmar, _hash_v1
from tests.versioning.test_confirmar import _publicada

LEAN = {"lean_cronologia", "lean_ubicacion", "lean_edad", "lean_nacimiento"}
DOS_SITIOS = [
    {
        "descripcion": "Ondina amarra en el puerto",
        "orden": 1,
        "lugar": "el puerto",
        "personajes": ["Ondina"],
        "anio": None,
        "edades": [],
    },
    {
        "descripcion": "Ondina enciende el faro",
        "orden": 1,
        "lugar": "el faro",
        "personajes": ["Ondina"],
        "anio": None,
        "edades": [],
    },
]


def con_formal(e: Entorno, **formal: Any) -> None:
    cfg = e.recursos.config
    nueva = cfg.model_copy(
        update={
            "umbrales": cfg.umbrales.model_copy(
                update={"formal": cfg.umbrales.formal.model_copy(update=formal)}
            )
        }
    )
    e.recursos = dataclasses.replace(e.recursos, config=nueva)


def _en_dos_sitios(p: Peticion, **kw: Any) -> dict[str, Any]:
    salida = _extraer(p, **kw)
    salida["eventos"] = DOS_SITIOS
    return salida


async def _generar(e: Entorno) -> tuple[str, Any]:
    novela = await e.crear_novela(brief_ejemplo())
    g = await cola.lanzar_generacion(e.recursos, novela)
    await e.orquestador().ejecutar(str(g.generacion_id))
    [final] = await cola.listar_generaciones(e.recursos, novela)
    return novela, final


@pytest.mark.anyio
async def test_una_candidata_con_una_violacion_no_se_publica(entorno: Entorno) -> None:
    con_formal(entorno, gate_activo=True, lean_incremental=False)
    guion_completo(entorno.modelo)
    entorno.modelo.encolar("extractor", *[partial(_en_dos_sitios, n=n) for n in range(1, 11)])
    novela, g = await _generar(entorno)

    assert g.estado == "Detenida", g
    [v] = entorno.consultar("SELECT estado FROM version_novela WHERE novel_id = ?", novela)
    assert v["estado"] == "rechazada"
    ubicacion = entorno.trazas.scores_de("lean_ubicacion")
    assert [s.valor for s in ubicacion] == [0.0]
    assert "capítulo 1" in (ubicacion[0].comentario or "")
    assert "Ondina" in (ubicacion[0].comentario or "")
    assert ubicacion[0].metadata == {"etapa": "gate"}
    for nombre in LEAN - {"lean_ubicacion"}:
        assert [s.valor for s in entorno.trazas.scores_de(nombre)] == [1.0], nombre
    [detencion] = entorno.consultar(
        "SELECT entrada FROM audit_log WHERE novel_id = ? AND resultado = 'detener'", novela
    )
    assert "lean_ubicacion" in detencion["entrada"] and "capítulo 1" in detencion["entrada"]


@pytest.mark.anyio
async def test_una_candidata_limpia_se_publica_con_los_cuatro_scores(entorno: Entorno) -> None:
    con_formal(entorno, gate_activo=True, lean_incremental=False)
    guion_completo(entorno.modelo)
    _, g = await _generar(entorno)

    assert g.estado == "Publicada", g
    for nombre in LEAN:
        assert [s.valor for s in entorno.trazas.scores_de(nombre)] == [1.0], nombre
    assert "lean" in entorno.trazas.nombres("span")


@pytest.mark.anyio
async def test_con_el_gate_apagado_lean_no_corre(entorno: Entorno) -> None:
    con_formal(entorno, gate_activo=False, lean_incremental=False)
    guion_completo(entorno.modelo)
    _, g = await _generar(entorno)

    assert g.estado == "Publicada", g
    assert not any(entorno.trazas.scores_de(n) for n in LEAN)
    assert "lean" not in entorno.trazas.nombres("span")


@pytest.mark.anyio
async def test_una_regeneracion_en_rojo_deja_intacta_la_publicada(entorno: Entorno) -> None:
    con_formal(entorno, gate_activo=True, lean_incremental=False)
    novela = await _publicada(entorno)
    hash_antes = _hash_v1(entorno, novela)
    entorno.modelo.por_defecto["extractor"] = partial(_en_dos_sitios, n=102)
    g = await _confirmar(entorno, novela)
    await entorno.orquestador().ejecutar(str(g.generacion_id))

    versiones = entorno.consultar(
        "SELECT version, estado FROM version_novela WHERE novel_id = ? ORDER BY version", novela
    )
    assert [(v["version"], v["estado"]) for v in versiones] == [(1, "publicada"), (2, "rechazada")]
    assert _hash_v1(entorno, novela) == hash_antes
    [obra] = entorno.consultar("SELECT estado FROM obra WHERE novel_id = ?", novela)
    assert obra["estado"] == "Publicada"
