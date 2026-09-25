"""El extractor devuelve año, edad declarada y eventos excluyentes, y la aceptación los
consolida solo si el texto los dijo (RF-LEAN-06, TO-064, TO-065)."""

from __future__ import annotations

import json

import pytest

from app.process.aceptar import ESQUEMA_EXTRACCION
from tests.conftest import Entorno
from tests.fixtures.planificada import novela_planificada
from tests.process.test_aceptar import _capitulo_aceptado

CON_ANIO = [
    {
        "descripcion": "Ondina cumple diez años en el puerto",
        "orden": 1,
        "lugar": "el puerto",
        "personajes": ["Ondina"],
        "anio": 1998,
        "edades": [{"personaje": "Ondina", "edad": 10}],
    },
    {
        "descripcion": "El farero muere en la tormenta",
        "orden": 2,
        "lugar": "el puerto",
        "personajes": ["Ondina"],
        "anio": 1998,
        "edades": [],
    },
]


def _eventos(e: Entorno, cid: str) -> list[dict[str, object]]:
    return [
        dict(f)
        for f in e.consultar(
            "SELECT ev.id, ev.momento, ev.anio, ep.edad FROM evento ev"
            " JOIN evento_capitulo ec ON ec.evento_id = ev.id"
            " LEFT JOIN evento_personaje ep ON ep.evento_id = ev.id"
            " WHERE ec.capitulo_id = ? ORDER BY ev.momento",
            cid,
        )
    ]


def test_el_esquema_pide_anio_edades_y_excluyentes() -> None:
    texto = json.dumps(ESQUEMA_EXTRACCION)
    for campo in ('"anio"', '"edades"', '"excluyentes"'):
        assert campo in texto


@pytest.mark.anyio
async def test_anio_edad_y_muerte_explicitos_se_consolidan(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    cid = await _capitulo_aceptado(
        entorno,
        novela,
        eventos=CON_ANIO,
        excluyentes=[{"personaje": "Ondina", "tipo": "partida", "orden": 2}],
    )
    filas = _eventos(entorno, cid)
    assert [(f["momento"], f["anio"], f["edad"]) for f in filas] == [
        (101, 1998, 10),
        (102, 1998, None),
    ]
    [x] = entorno.consultar(
        "SELECT x.tipo, e.momento FROM evento_excluyente x JOIN evento e ON e.id = x.evento_id"
        " WHERE x.novel_id = ?",
        novela,
    )
    assert (x["tipo"], x["momento"]) == ("partida", 102)


@pytest.mark.anyio
async def test_sin_datos_explicitos_quedan_nulos(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    cid = await _capitulo_aceptado(entorno, novela)
    assert [(f["anio"], f["edad"]) for f in _eventos(entorno, cid)] == [(None, None)]
    assert entorno.consultar("SELECT 1 FROM evento_excluyente WHERE novel_id = ?", novela) == []


@pytest.mark.anyio
async def test_un_excluyente_que_no_casa_no_se_inventa(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    await _capitulo_aceptado(
        entorno,
        novela,
        eventos=CON_ANIO,
        excluyentes=[
            {"personaje": "Ondina", "tipo": "muerte", "orden": 9},
            {"personaje": "Nadie Conocido", "tipo": "muerte", "orden": 1},
        ],
    )
    assert entorno.consultar("SELECT 1 FROM evento_excluyente WHERE novel_id = ?", novela) == []
    descartes = entorno.consultar(
        "SELECT entrada FROM audit_log WHERE novel_id = ? AND regla = 'excluyente-sin-evento'",
        novela,
    )
    assert len(descartes) == 2


@pytest.mark.anyio
async def test_una_edad_de_alguien_que_no_esta_en_el_evento_no_se_guarda(
    entorno: Entorno,
) -> None:
    novela = await novela_planificada(entorno)
    eventos = [dict(CON_ANIO[0], edades=[{"personaje": "Nadie Conocido", "edad": 3}])]
    cid = await _capitulo_aceptado(entorno, novela, eventos=eventos)
    assert [f["edad"] for f in _eventos(entorno, cid)] == [None]
