"""Generador determinista del fichero Lean (RF-LEAN-01, A-90, A-91, regla 11)."""

from __future__ import annotations

import random
import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.novel.service import EventoVigente, PresenciaEnEvento
from app.versioning.lean.generar import (
    Cronologia,
    ExcluyenteDeVersion,
    PersonajeDeVersion,
    generar,
    leer_cronologia,
)
from tests.conftest import Entorno
from tests.fixtures.planificada import novela_planificada
from tests.process.test_aceptar import _capitulo_aceptado
from tests.process.test_extraccion_temporal import CON_ANIO

MARCA = "TEXTO-LIBRE-QUE-NO-DEBE-ENTRAR"

_uuid = st.uuids().map(str)


@st.composite
def cronologias(draw: st.DrawFn) -> Cronologia:
    personajes = draw(st.lists(_uuid, min_size=1, max_size=4, unique=True))
    lugares = draw(st.lists(_uuid, max_size=3, unique=True))
    ids = draw(st.lists(_uuid, min_size=1, max_size=8, unique=True))
    eventos = []
    for i, eid in enumerate(ids):
        presentes = draw(st.lists(st.sampled_from(personajes), max_size=3, unique=True))
        eventos.append(
            EventoVigente(
                evento_id=eid,
                capitulo_id=f"c{i // 3 + 1}",
                numero=i // 3 + 1,
                momento=(i // 3 + 1) * 100 + i % 3 + 1,
                descripcion=f"{MARCA} evento {i}",
                anio=draw(st.none() | st.integers(1900, 2030)),
                lugar_id=draw(st.none() | st.sampled_from(lugares)) if lugares else None,
                presentes=[
                    PresenciaEnEvento(personaje_id=p, edad=draw(st.none() | st.integers(0, 99)))
                    for p in presentes
                ],
            )
        )
    excluyentes = [
        ExcluyenteDeVersion(evento_id=draw(st.sampled_from(ids)), personaje_id=p, tipo="muerte")
        for p in draw(st.lists(st.sampled_from(personajes), max_size=2, unique=True))
    ]
    return Cronologia(
        novel_id=draw(_uuid),
        version=1,
        eventos=eventos,
        excluyentes=excluyentes,
        personajes=[
            PersonajeDeVersion(
                personaje_id=p,
                nombre=f"{MARCA} {p}",
                anio_nacimiento=draw(st.none() | st.integers(1900, 2030)),
            )
            for p in personajes
        ],
    )


def _barajada(c: Cronologia, semilla: int) -> Cronologia:
    r = random.Random(semilla)
    eventos = list(c.eventos)
    r.shuffle(eventos)
    eventos = [
        e.model_copy(update={"presentes": r.sample(e.presentes, len(e.presentes))}) for e in eventos
    ]
    return c.model_copy(
        update={
            "eventos": eventos,
            "excluyentes": r.sample(c.excluyentes, len(c.excluyentes)),
            "personajes": r.sample(c.personajes, len(c.personajes)),
        }
    )


@settings(max_examples=60, deadline=None)
@given(cronologias(), st.integers(0, 1000))
def test_misma_story_bible_mismo_fichero_en_cualquier_orden(c: Cronologia, semilla: int) -> None:
    assert generar(c).texto == generar(c).texto
    assert generar(_barajada(c, semilla)).texto == generar(c).texto


@settings(max_examples=60, deadline=None)
@given(cronologias())
def test_sin_mathlib_ni_texto_libre(c: Cronologia) -> None:
    texto = generar(c).texto
    assert MARCA not in texto
    assert "import Mathlib" not in texto
    assert re.findall(r"^import .*$", texto, re.MULTILINE) == ["import Cronologia.Basico"]


@settings(max_examples=60, deadline=None)
@given(cronologias())
def test_cuatro_teoremas_por_evento_y_el_indice_los_cubre(c: Cronologia) -> None:
    fichero = generar(c)
    lineas = fichero.texto.splitlines()
    teoremas = [i + 1 for i, ln in enumerate(lineas) if ln.startswith("theorem ")]
    assert len(teoremas) == 4 * len(c.eventos)
    assert sorted(fichero.indice) == teoremas
    ids = {e.evento_id for e in c.eventos}
    for linea, t in fichero.indice.items():
        assert t.evento_id in ids
        assert lineas[linea - 1].startswith(f"theorem {t.invariante}_")
    assert {t.invariante for t in fichero.indice.values()} == (
        {"ubicacion", "cronologia", "edad", "nacimiento"}
    )


@pytest.mark.anyio
async def test_lee_solo_la_version_y_hasta_el_capitulo_pedido(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    await _capitulo_aceptado(
        entorno,
        novela,
        numero=1,
        eventos=CON_ANIO,
        excluyentes=[{"personaje": "Ondina", "tipo": "partida", "orden": 2}],
    )
    await _capitulo_aceptado(entorno, novela, numero=2)

    completa = await entorno.recursos.db.ejecutar(
        lambda con: leer_cronologia(con, novel_id=novela, version=1)
    )
    hasta_uno = await entorno.recursos.db.ejecutar(
        lambda con: leer_cronologia(con, novel_id=novela, version=1, hasta_numero=1)
    )
    assert [e.momento for e in completa.eventos] == [101, 102, 201]
    assert [e.momento for e in hasta_uno.eventos] == [101, 102]
    assert [e.anio for e in hasta_uno.eventos] == [1998, 1998]
    assert [(x.tipo) for x in completa.excluyentes] == ["partida"]
    ondina = next(p for p in completa.personajes if p.nombre == "Ondina")
    texto = generar(completa).texto
    assert "Ondina" not in texto
    assert ondina.personaje_id in texto  # solo en el comentario que enlaza ids sintéticos
