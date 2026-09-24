"""Gate de publicación: `cierre_arco` (RF-QUA-03, D-15, D-17). Una promesa pendiente al cerrar
el último capítulo impide publicar, y el fallo devuelve la novela al editor."""

from __future__ import annotations

import json
from functools import partial
from typing import Any

from app.commons.llm import Peticion
from tests.conftest import Instancia
from tests.dobles.guiones import capitulo_aceptado_de, guion_completo
from tests.fixtures.briefs import brief_ejemplo
from tests.fixtures.extracciones import extraccion
from tests.process.test_orquestador import esperar

ELEMENTOS = [e["enunciado"] for e in brief_ejemplo()["elementos_personalizados"]]
PROMESA = "¿Volverá el Alondra a navegar?"


def _extraer(peticion: Peticion, **kw: Any) -> dict[str, Any]:
    return extraccion(capitulo_aceptado_de(peticion), elementos=ELEMENTOS, **kw)


def _lanzar(i: Instancia) -> tuple[str, dict[str, Any]]:
    novela = i.cliente.post("/novelas", json=brief_ejemplo()).json()["novel_id"]
    gid = i.cliente.post(f"/novelas/{novela}/generaciones").json()["generacion_id"]
    return novela, esperar(i.cliente, novela, gid, lambda g: g["es_terminal"])


def test_una_promesa_pendiente_al_cerrar_impide_publicar(instancia: Instancia) -> None:
    guion_completo(instancia.modelo)
    instancia.modelo.encolar("extractor", partial(_extraer, promesas=[PROMESA]))
    novela, g = _lanzar(instancia)

    assert g["estado"] == "Detenida", g
    assert g["detenida_por"] == "error-interno"
    assert g["version_resultante"] is None
    assert instancia.cliente.get(f"/novelas/{novela}/versiones").json() == []
    assert [s.valor for s in instancia.trazas.scores_de("cierre_arco")][-1] == 0.0

    recursos = instancia.app.state.recursos
    filas = recursos.db.ejecutar_sync(
        lambda con: con.execute(
            "SELECT entrada FROM audit_log WHERE novel_id = ? AND sujeto = 'generacion'",
            (novela,),
        ).fetchall()
    )
    entrada = json.loads(filas[-1]["entrada"])
    assert "cierre_arco" in entrada["detalle"] and PROMESA in entrada["detalle"]
    # Como dibuja el diagrama: el gate en rojo devuelve la novela al editor (Escribiendo).
    assert entrada["transiciones"] == ["DevolverAlEditor", "Detener"]


def test_una_promesa_abierta_y_pagada_despues_deja_publicar(instancia: Instancia) -> None:
    guion_completo(instancia.modelo)
    defecto = partial(_extraer)
    instancia.modelo.encolar(
        "extractor",
        partial(_extraer, promesas=[PROMESA]),
        defecto,
        defecto,
        partial(_extraer, pagadas=["P1"]),
    )
    _, g = _lanzar(instancia)
    assert g["estado"] == "Publicada", g
    assert [s.valor for s in instancia.trazas.scores_de("cierre_arco")][-1] == 1.0
