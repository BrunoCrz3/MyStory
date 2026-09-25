"""`cierre_arco` sobre el último capítulo de una generación inicial (TO-056).

Visto en el ensayo de la demo: el capítulo 10 abrió una promesa nueva, se consolidó, y el gate
rechazó la versión entera cuando ya no quedaba capítulo que pudiera pagarla. El último capítulo
pasa ahora la mitad programática de `cierre_arco` antes de consolidarse, como un capítulo
reescrito (TO-047): si deja promesas pendientes al cierre, vuelve a su redactor como intento
fallido.
"""

from __future__ import annotations

from functools import partial
from typing import Any

import pytest

from app.commons.llm import Peticion
from app.process import cola
from tests.canon.test_hechos_por_version import _extraer
from tests.conftest import Entorno
from tests.dobles.guiones import guion_completo, numero_de_la_tarea
from tests.fixtures.briefs import brief_ejemplo
from tests.process.test_regeneracion_promesas import DEVUELTO, alias

VIEJA = "¿Volverá el Alondra a navegar?"
DESEO = "¿Qué deseo pidió Ondina al soplar las velas?"


def _cierre_del_ultimo(trazas: Any) -> list[float]:
    return [
        s.valor
        for s in trazas.scores_de("cierre_arco")
        if s.comentario and "último capítulo" in s.comentario
    ]


async def _generar(e: Entorno, *ultimos: Any) -> tuple[str, Any]:
    """Una generación inicial: el capítulo 5 abre `VIEJA` y el 10 extrae con `ultimos`, uno por
    intento."""
    guion_completo(e.modelo)
    guiones = [partial(_extraer, n=n) for n in range(1, 10)]
    guiones[4] = partial(_extraer, n=5, promesas=[VIEJA])
    e.modelo.encolar("extractor", *guiones, *ultimos)
    novela = await e.crear_novela(brief_ejemplo())
    g = await cola.lanzar_generacion(e.recursos, novela)
    await e.orquestador().ejecutar(str(g.generacion_id))
    [generacion] = await cola.listar_generaciones(e.recursos, novela)
    return novela, generacion


def _redactor_del_ultimo(e: Entorno) -> list[str]:
    return [
        p.mensajes[0].contenido
        for p in e.modelo.peticiones
        if p.rol == "redactor" and numero_de_la_tarea(p) == 10
    ]


def _paga_la_vieja(p: Peticion) -> dict[str, Any]:
    return _extraer(p, n=10, pagadas=[alias(p, VIEJA)])


@pytest.mark.anyio
async def test_una_promesa_nueva_en_el_ultimo_vuelve_al_redactor_y_la_novela_se_publica(
    entorno: Entorno,
) -> None:
    def abre_el_deseo(p: Peticion) -> dict[str, Any]:
        return _extraer(p, n=10, promesas=[DESEO], pagadas=[alias(p, VIEJA)])

    novela, g = await _generar(entorno, abre_el_deseo, _paga_la_vieja)

    assert g.estado == "Publicada", g
    redactor = _redactor_del_ultimo(entorno)
    assert len(redactor) == 2 and DESEO in redactor[1].partition(DEVUELTO)[2]
    [cap] = entorno.consultar(
        "SELECT id, intentos FROM capitulo WHERE novel_id = ? AND numero = 10", novela
    )
    assert cap["intentos"] == 1
    decisiones = entorno.consultar(
        "SELECT resultado, entrada FROM audit_log WHERE sujeto = 'capitulo' AND sujeto_id = ?"
        " ORDER BY rowid",
        cap["id"],
    )
    assert [d["resultado"] for d in decisiones] == ["aceptar", "devolver", "aceptar"]
    assert "cierre_arco" in decisiones[1]["entrada"]
    # La extracción descartada no deja rastro.
    assert not entorno.consultar("SELECT 1 FROM promesa WHERE enunciado = ?", DESEO)
    assert _cierre_del_ultimo(entorno.trazas) == [0.0, 1.0]


@pytest.mark.anyio
async def test_una_promesa_vieja_que_el_ultimo_no_paga_tambien_devuelve(entorno: Entorno) -> None:
    def olvida_la_vieja(p: Peticion) -> dict[str, Any]:
        return _extraer(p, n=10)

    _, g = await _generar(entorno, olvida_la_vieja, _paga_la_vieja)

    assert g.estado == "Publicada", g
    redactor = _redactor_del_ultimo(entorno)
    assert len(redactor) == 2 and VIEJA in redactor[1].partition(DEVUELTO)[2]
    assert _cierre_del_ultimo(entorno.trazas) == [0.0, 1.0]


@pytest.mark.anyio
async def test_los_capitulos_intermedios_pueden_abrir_promesas(entorno: Entorno) -> None:
    """Solo el último se comprueba: el 5 abre una que el 10 paga y nada vuelve atrás."""
    _, g = await _generar(entorno, _paga_la_vieja)

    assert g.estado == "Publicada", g
    assert len(_redactor_del_ultimo(entorno)) == 1
    assert _cierre_del_ultimo(entorno.trazas) == [1.0]
