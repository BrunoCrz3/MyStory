"""Promesas en la regeneración dirigida (RF-VER-08, O-34, TO-047).

La novela de estas pruebas tiene tres promesas en la versión 1:

- A, abierta por el 2 y pagada por el 9, que no se reescribe;
- B, abierta por el 2 y pagada por el 7, que se reescriben los dos;
- C, abierta por el 5, que no se reescribe, y pagada por el 7.

El cambio de hecho reescribe el 2 y el 7. El capítulo reescrito conserva las promesas que su
versión anterior abría y pagaba, el extractor las reabre por su alias en vez de duplicarlas,
y una promesa que se quedaría pendiente vuelve al redactor como intento fallido.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from functools import partial
from typing import Any

import pytest

from app.canon import service as canon
from app.commons.llm import Peticion
from app.process import cola
from app.versioning import confirmar
from tests.canon.test_hechos_por_version import _extraer
from tests.conftest import Entorno
from tests.dobles.guiones import capitulo_aceptado_de, guion_completo, numero_de_la_tarea, redactar
from tests.fixtures.borradores import borrador
from tests.fixtures.briefs import brief_ejemplo
from tests.versioning.test_confirmar import _solicitud

NUEVO = "El perro se llama Nala"
A = "¿Volverá el Alondra a navegar?"
B = "¿Quién dejó la carta en el muelle?"
C = "¿Encontrará Ondina el faro apagado?"
INTRUSA = "¿Qué esconde Nala bajo la barca?"
CORREGIDO = "Ondina volvió a preguntarse por la carta y por el Alondra."
DEVUELTO = "El borrador anterior no pasó la validación"


def alias(peticion: Peticion, enunciado: str) -> str:
    """El alias con que el extractor recibe una promesa viva (`P1: …`)."""
    m = re.search(r"(P\d+): " + re.escape(enunciado), peticion.mensajes[0].contenido)
    assert m, f"el extractor no recibió la promesa {enunciado!r}"
    return m.group(1)


def capitulo_de(peticion: Peticion) -> int:
    m = re.search(r"en el capítulo (\d+)", capitulo_aceptado_de(peticion))
    return int(m.group(1)) if m else 0


def _v1(p: Peticion, n: int) -> dict[str, Any]:
    if n == 2:
        return _extraer(p, n=2, promesas=[A, B])
    if n == 5:
        return _extraer(p, n=5, promesas=[C])
    if n == 7:
        return _extraer(p, n=7, usados=["H2"], pagadas=[alias(p, B), alias(p, C)])
    if n == 9:
        return _extraer(p, n=9, pagadas=[alias(p, A)])
    return _extraer(p, n=n)


def _redactor(p: Peticion) -> dict[str, str]:
    """Si el contexto trae el hecho nuevo, reescribe; si trae una corrección de promesas, la
    atiende. El texto dice su número, para que el extractor sepa qué capítulo lee."""
    contenido = p.mensajes[0].contenido
    if NUEVO not in contenido:
        return redactar(p)
    n = numero_de_la_tarea(p)
    extra = f"{NUEVO}, y ladró al verla llegar en el capítulo {n}."
    _, _, correccion = contenido.partition(DEVUELTO)
    if "promesa" in correccion:
        extra += " " + CORREGIDO
    return borrador(titulo=f"Capítulo {n}: Nala", extra=extra)


Extractor = Callable[[Peticion, int, bool], dict[str, Any]]


def _fiel(p: Peticion, n: int, corregido: bool) -> dict[str, Any]:
    """Reabre lo que abría y paga lo que pagaba."""
    if n == 2:
        return _extraer(p, n=102, reabiertas=[alias(p, A), alias(p, B)])
    return _extraer(p, n=107, pagadas=[alias(p, B), alias(p, C)])


async def _publicada(e: Entorno) -> str:
    guion_completo(e.modelo)
    e.modelo.encolar("extractor", *[partial(_v1, n=n) for n in range(1, 11)])
    novela = await e.crear_novela(brief_ejemplo())
    g = await cola.lanzar_generacion(e.recursos, novela)
    await e.orquestador().ejecutar(str(g.generacion_id))
    return novela


async def _regenerar(e: Entorno, extractor: Extractor) -> tuple[str, Any, dict[str, canon.Promesa]]:
    novela = await _publicada(e)
    v1 = _promesas(e, novela, 1)
    sid, _ = await _solicitud(e, novela)
    e.modelo.por_defecto["redactor"] = _redactor

    def extraer(p: Peticion) -> dict[str, Any]:
        return extractor(p, capitulo_de(p), CORREGIDO in capitulo_aceptado_de(p))

    e.modelo.por_defecto["extractor"] = extraer
    g = await confirmar.confirmar(e.recursos, novela, sid)
    await e.orquestador().ejecutar(str(g.generacion_id))
    generaciones = await cola.listar_generaciones(e.recursos, novela)
    [dirigida] = [x for x in generaciones if x.tipo == "dirigida"]
    return novela, dirigida, v1


def _promesas(e: Entorno, novela: str, version: int) -> dict[str, canon.Promesa]:
    filas = e.consultar(
        "SELECT capitulo_id FROM version_capitulo WHERE novel_id = ? AND version = ?",
        novela,
        version,
    )
    ids = [f["capitulo_id"] for f in filas]
    promesas = e.recursos.db.ejecutar_sync(
        lambda con: canon.promesas_de(con, novel_id=novela, version=version, capitulo_ids=ids)
    )
    return {p.enunciado: p for p in promesas}


def _redactor_de(e: Entorno, numero: int) -> list[str]:
    return [
        p.mensajes[0].contenido
        for p in e.modelo.peticiones
        if p.rol == "redactor"
        and numero_de_la_tarea(p) == numero
        and NUEVO in p.mensajes[0].contenido
    ]


def cierre_programatico(trazas: Any) -> list[float]:
    """Los scores de la mitad programática de `cierre_arco`: la de cada capítulo reescrito y la
    del gate. El judge puntúa la semántica con el mismo nombre."""
    return [
        s.valor
        for s in trazas.scores_de("cierre_arco")
        if s.comentario and ("reescrito" in s.comentario or "al cerrar" in s.comentario)
    ]


def _capa(contenido: str, nombre: str) -> str:
    return contenido.split(f'<capa nombre="{nombre}">', 1)[1].split("</capa>", 1)[0]


@pytest.mark.anyio
async def test_el_redactor_recibe_como_destino_las_promesas_que_abria_y_pagaba(
    entorno: Entorno,
) -> None:
    _, g, _ = await _regenerar(entorno, _fiel)
    assert g.estado == "Publicada", g

    [segundo] = _redactor_de(entorno, 2)
    estructural = _capa(segundo, "estructural")
    assert "Promesas que este capítulo conserva" in estructural
    assert re.search(r"P\d+ \[abrir\]: " + re.escape(A), estructural)
    assert re.search(r"P\d+ \[abrir\]: " + re.escape(B), estructural)
    assert "No abras promesas nuevas" in estructural

    [septimo] = _redactor_de(entorno, 7)
    estructural = _capa(septimo, "estructural")
    assert re.search(r"P\d+ \[pagar\]: " + re.escape(B), estructural)
    assert re.search(r"P\d+ \[pagar\]: " + re.escape(C), estructural)
    assert A not in estructural  # la paga el 9, que no se reescribe


@pytest.mark.anyio
async def test_el_extractor_reabre_por_alias_y_la_version_1_no_cambia(entorno: Entorno) -> None:
    novela, g, antes = await _regenerar(entorno, _fiel)
    assert g.estado == "Publicada" and g.version_resultante == 2, g

    v1, v2 = _promesas(entorno, novela, 1), _promesas(entorno, novela, 2)
    assert v1 == antes  # la versión 1 se lee igual que antes de regenerar
    assert sorted(v2) == sorted([A, B, C])
    # Reabiertas, no duplicadas: sigue habiendo tres promesas en la story bible.
    assert entorno.consultar("SELECT count(*) AS n FROM promesa")[0]["n"] == 3
    assert all(p.estado == "pagada" for p in v2.values())
    assert (v2[A].capitulo_apertura, v2[A].capitulo_pago) == (2, 9)
    assert (v2[B].capitulo_apertura, v2[B].capitulo_pago) == (2, 7)
    assert (v2[C].capitulo_apertura, v2[C].capitulo_pago) == (5, 7)
    assert (v1[A].capitulo_pago, v1[B].capitulo_pago, v1[C].capitulo_pago) == (9, 7, 7)
    assert cierre_programatico(entorno.trazas)[-1] == 1.0


@pytest.mark.anyio
async def test_una_promesa_vieja_se_cierra_solo_si_nadie_la_reabre_ni_la_paga(
    entorno: Entorno,
) -> None:
    def sin_reabrir(p: Peticion, n: int, corregido: bool) -> dict[str, Any]:
        if n == 2:
            return _extraer(p, n=102)
        return _extraer(p, n=107, pagadas=[alias(p, C)])

    novela, g, antes = await _regenerar(entorno, sin_reabrir)
    assert g.estado == "Publicada", g

    v2 = _promesas(entorno, novela, 2)
    # A la paga el 9, que no cambia: no se cierra. B solo la pagaba el 7, que se reescribió.
    assert sorted(v2) == sorted([A, C])
    assert (v2[A].estado, v2[A].capitulo_pago) == ("pagada", 9)
    assert _promesas(entorno, novela, 1) == antes

    [septimo] = _redactor_de(entorno, 7)
    assert B not in _capa(septimo, "estructural")
    # El snapshot del 6, que no se reescribe, se lee desde la versión 2: A sigue abierta
    # porque la paga el 9, y B ya no existe.
    estado = _capa(septimo, "estado")
    assert A in estado and C in estado and B not in estado


@pytest.mark.anyio
async def test_una_promesa_nueva_sin_pago_vuelve_al_redactor_como_intento_fallido(
    entorno: Entorno,
) -> None:
    def tiende_a_abrir(p: Peticion, n: int, corregido: bool) -> dict[str, Any]:
        if n == 2 and not corregido:
            return _extraer(p, n=102, promesas=[INTRUSA], reabiertas=[alias(p, A), alias(p, B)])
        return _fiel(p, n, corregido)

    novela, g, _ = await _regenerar(entorno, tiende_a_abrir)
    assert g.estado == "Publicada", g

    segundos = _redactor_de(entorno, 2)
    assert len(segundos) == 2
    assert INTRUSA in segundos[1].partition(DEVUELTO)[2]

    [cap] = entorno.consultar(
        "SELECT id, intentos FROM capitulo WHERE novel_id = ? AND numero = 2 AND version = 2",
        novela,
    )
    assert cap["intentos"] == 1
    decisiones = entorno.consultar(
        "SELECT regla, resultado, entrada FROM audit_log WHERE sujeto = 'capitulo'"
        " AND sujeto_id = ? AND regla <> 'lean-incremental' ORDER BY rowid",
        cap["id"],
    )
    assert [d["resultado"] for d in decisiones] == ["aceptar", "devolver", "aceptar"]
    assert "cierre_arco" in decisiones[1]["entrada"]
    # La extracción descartada no deja rastro: ni la promesa intrusa ni duplicados.
    assert INTRUSA not in _promesas(entorno, novela, 2)
    assert entorno.consultar("SELECT count(*) AS n FROM promesa")[0]["n"] == 3
    # El gate de la 1; el 2 reescrito, dos veces; el 7; y el gate de la 2.
    assert cierre_programatico(entorno.trazas) == [1.0, 0.0, 1.0, 1.0, 1.0]


@pytest.mark.anyio
async def test_dejar_sin_pagar_lo_que_pagaba_la_version_anterior_tambien_devuelve(
    entorno: Entorno,
) -> None:
    def olvida_c(p: Peticion, n: int, corregido: bool) -> dict[str, Any]:
        if n == 7 and not corregido:
            return _extraer(p, n=107, pagadas=[alias(p, B)])
        return _fiel(p, n, corregido)

    novela, g, _ = await _regenerar(entorno, olvida_c)
    assert g.estado == "Publicada", g
    septimos = _redactor_de(entorno, 7)
    assert len(septimos) == 2 and C in septimos[1].partition(DEVUELTO)[2]
    assert _promesas(entorno, novela, 2)[C].capitulo_pago == 7


@pytest.mark.anyio
async def test_si_se_agotan_los_intentos_la_regeneracion_se_detiene(entorno: Entorno) -> None:
    def siempre_abre(p: Peticion, n: int, corregido: bool) -> dict[str, Any]:
        if n == 2:
            return _extraer(p, n=102, promesas=[INTRUSA], reabiertas=[alias(p, A), alias(p, B)])
        return _fiel(p, n, corregido)

    novela, g, _ = await _regenerar(entorno, siempre_abre)
    assert g.estado == "Detenida" and g.detenida_por == "limite-de-intentos-agotado", g
    assert g.version_resultante is None
    limite = entorno.recursos.config.umbrales.orquestacion.max_intentos_capitulo
    assert len(_redactor_de(entorno, 2)) == limite + 1
    [cap] = entorno.consultar(
        "SELECT estado FROM capitulo WHERE novel_id = ? AND numero = 2 AND version = 2", novela
    )
    assert cap["estado"] == "Agotado"
    # TO-062: la generación se detiene, pero la novela sigue publicada con la versión 1, y la
    # candidata queda rechazada.
    [obra] = entorno.consultar("SELECT estado FROM obra WHERE novel_id = ?", novela)
    assert obra["estado"] == "Publicada"
    [v2] = entorno.consultar(
        "SELECT estado FROM version_novela WHERE novel_id = ? AND version = 2", novela
    )
    assert v2["estado"] == "rechazada"
