"""Editor y orden completo de validación: policy → capítulo → judge → editor, y el borrador
corregido vuelve a pasar todos los validadores (RF-QUA-05, RF-NOVEL-04, D-14)."""

from __future__ import annotations

import json

import pytest

from app.process.capitulo import ciclo_capitulo
from tests.conftest import Entorno
from tests.dobles.guiones import corregido
from tests.fixtures.borradores import borrador
from tests.fixtures.judge import salida_judge
from tests.fixtures.planificada import novela_planificada

VETADA = "Luis la esperaba en el puerto aquella tarde de viento."


@pytest.mark.anyio
async def test_el_editor_corrige_un_defecto_que_cierra_el_paso(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    entorno.modelo.encolar("redactor", borrador(500))
    entorno.modelo.encolar("editor", corregido())
    r = await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=1)
    assert r.accion == "aceptar" and r.intentos == 0
    assert entorno.modelo.llamadas["redactor"] == 1
    # El editor recibió el informe con el defecto de longitud.
    editor = next(p for p in entorno.modelo.peticiones if p.rol == "editor")
    assert "500 palabras" in editor.mensajes[0].contenido
    assert [s.valor for s in entorno.trazas.scores_de("longitud")] == [0.0, 1.0]


@pytest.mark.anyio
async def test_el_corregido_vuelve_a_pasar_todos_los_validadores(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    # El editor arregla la longitud pero mete una palabra vetada: el hook de policy lo caza.
    entorno.modelo.encolar("redactor", borrador(500), borrador())
    entorno.modelo.encolar("editor", corregido(extra=VETADA))
    r = await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=1)
    assert r.accion == "aceptar" and r.intentos == 1
    assert [s.valor for s in entorno.trazas.scores_de("palabras_prohibidas")] == [1.0, 0.0, 1.0]
    coincidencias = entorno.consultar("SELECT palabra, intento FROM coincidencia")
    assert [tuple(c) for c in coincidencias] == [("Luis", 0)]


@pytest.mark.anyio
async def test_el_orden_de_llamadas_es_writer_validadores_judge_editor(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    entorno.modelo.encolar("redactor", borrador(500))
    entorno.modelo.encolar("editor", corregido())
    await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=1)
    spans = [
        s
        for s in entorno.trazas.nombres()
        if s in ("writer", "hook_policy", "hook_capitulo", "judge", "editor")
    ]
    assert spans[:5] == ["writer", "hook_policy", "hook_capitulo", "judge", "editor"]
    # Y el corregido pasa otra vez por todo, judge incluido.
    assert spans[5:] == ["hook_policy", "hook_capitulo", "judge"]


@pytest.mark.anyio
async def test_sin_defectos_que_cierren_no_se_llama_al_editor(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    entorno.modelo.encolar("redactor", borrador())
    r = await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=1)
    assert r.accion == "aceptar"
    assert entorno.modelo.llamadas["judge"] == 1
    assert entorno.modelo.llamadas["editor"] == 0


@pytest.mark.anyio
async def test_si_falla_el_hook_de_policy_no_se_paga_ni_judge_ni_editor(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    entorno.modelo.encolar("redactor", borrador(extra=VETADA), borrador())
    await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=1)
    assert entorno.modelo.llamadas["judge"] == 1  # solo el del segundo borrador
    assert entorno.modelo.llamadas["editor"] == 0


@pytest.mark.anyio
async def test_un_defecto_sistemico_se_reescribe_como_local_y_queda_registrado(
    entorno: Entorno,
) -> None:
    novela = await novela_planificada(entorno)
    entorno.modelo.encolar("redactor", borrador(500))
    sistemico = {"defecto": "el destino del capítulo es imposible", "clasificacion": "sistémico"}
    entorno.modelo.encolar("editor", {**borrador(), "clasificacion": [sistemico]})
    r = await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=1)
    assert r.accion == "aceptar"  # D-14: no se replanifica
    [fila] = entorno.consultar(
        "SELECT sujeto, regla, entrada, resultado FROM audit_log"
        " WHERE regla = 'defecto-sistemico-como-local'"
    )
    entrada = json.loads(fila["entrada"])
    assert entrada["clasificacion"] == "sistémico"
    assert entrada["defecto"] == "el destino del capítulo es imposible"
    assert fila["resultado"] == "reescribir"


@pytest.mark.anyio
async def test_un_judge_que_suspende_con_la_medicion_cerrada_pasa_al_editor(
    entorno: Entorno,
) -> None:
    novela = await novela_planificada(entorno)
    u = entorno.recursos.config.umbrales
    entorno.recursos.config = entorno.recursos.config.model_copy(
        update={
            "umbrales": u.model_copy(
                update={"medicion": u.medicion.model_copy(update={"cerrar_el_paso": True})}
            )
        }
    )
    # Con la medición cerrada suspenden también los validadores con score; basta con que el
    # redactor tenga borradores para todos los intentos.
    limite = u.orquestacion.max_intentos_capitulo
    entorno.modelo.encolar("redactor", *[borrador()] * (limite + 1))
    entorno.modelo.encolar("judge", salida_judge(tono=0.1))
    await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=1)
    assert entorno.modelo.llamadas["editor"] >= 1
    editor = next(p for p in entorno.modelo.peticiones if p.rol == "editor")
    assert "Justificación de tono" in editor.mensajes[0].contenido
