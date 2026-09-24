"""Crear, listar y consultar novelas (RF-INTAKE-04, 05, RF-NOVEL-02, 03, RNF-10)."""

from __future__ import annotations

import uuid

from app.commons.recursos import Recursos
from app.guardrail.service import palabras_de_novela
from app.novel.service import reglas_del_mundo
from tests.conftest import Instancia, ValidarContrato
from tests.fixtures.briefs import brief_ejemplo


def _recursos(i: Instancia) -> Recursos:
    r: Recursos = i.app.state.recursos
    return r


def test_crear_novela_no_llama_al_modelo(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    r = instancia.cliente.post("/novelas", json=brief_ejemplo())
    assert r.status_code == 201
    validar_contra_contrato(r, "crearNovela")
    cuerpo = r.json()
    assert cuerpo["estado"] == "Configurando"
    assert cuerpo["titulo"] is None
    assert cuerpo["version_vigente"] is None
    assert cuerpo["total_capitulos"] == 10
    assert r.headers["location"] == f"/novelas/{cuerpo['novel_id']}"
    uuid.UUID(cuerpo["novel_id"])
    assert sum(instancia.modelo.llamadas.values()) == 0


def test_el_brief_se_devuelve_tal_cual(instancia: Instancia) -> None:
    brief = brief_ejemplo()
    creada = instancia.cliente.post("/novelas", json=brief).json()
    leida = instancia.cliente.get(f"/novelas/{creada['novel_id']}").json()
    assert leida["brief"]["destinatario"] == brief["destinatario"]
    assert leida["brief"]["dedicatoria"] == brief["dedicatoria"]
    assert leida["brief"]["palabras_prohibidas"] == brief["palabras_prohibidas"]


def test_palabras_y_reglas_quedan_asociadas_a_la_novela(instancia: Instancia) -> None:
    creada = instancia.cliente.post("/novelas", json=brief_ejemplo()).json()
    db = _recursos(instancia).db
    palabras = db.ejecutar_sync(lambda con: palabras_de_novela(con, novel_id=creada["novel_id"]))
    reglas = db.ejecutar_sync(lambda con: reglas_del_mundo(con, novel_id=creada["novel_id"]))
    assert [p.forma for p in palabras] == brief_ejemplo()["palabras_prohibidas"]
    assert all(p.nivel == "novela" for p in palabras)
    assert [r.enunciado for r in reglas] == brief_ejemplo()["reglas_mundo"]


def test_obtener_novela_cumple_el_contrato(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    creada = instancia.cliente.post("/novelas", json=brief_ejemplo()).json()
    r = instancia.cliente.get(f"/novelas/{creada['novel_id']}")
    assert r.status_code == 200
    validar_contra_contrato(r, "obtenerNovela")


def test_novela_inexistente_da_404(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    r = instancia.cliente.get(f"/novelas/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["type"] == "/problemas/novela-no-encontrada"
    validar_contra_contrato(r, "obtenerNovela")


def test_listar_pagina_de_la_mas_reciente_a_la_mas_antigua(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    ids = [
        instancia.cliente.post(
            "/novelas", json=brief_ejemplo(destinatario__nombre=f"Persona {n}")
        ).json()["novel_id"]
        for n in range(5)
    ]
    r = instancia.cliente.get("/novelas", params={"limite": 2, "desplazamiento": 1})
    assert r.status_code == 200
    validar_contra_contrato(r, "listarNovelas")
    cuerpo = r.json()
    assert cuerpo["total"] == 5
    assert [n["novel_id"] for n in cuerpo["items"]] == [ids[3], ids[2]]
    assert all(n["estado"] == "Configurando" for n in cuerpo["items"])


def test_limite_fuera_de_rango_da_422(instancia: Instancia) -> None:
    r = instancia.cliente.get("/novelas", params={"limite": 101})
    assert r.status_code == 422
    assert r.json()["type"] == "/problemas/peticion-invalida"


def test_brief_sin_campo_obligatorio_da_422_y_no_crea_nada(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    brief = brief_ejemplo()
    del brief["destinatario"]["nombre"]
    r = instancia.cliente.post("/novelas", json=brief)
    assert r.status_code == 422
    validar_contra_contrato(r, "crearNovela")
    assert instancia.cliente.get("/novelas").json()["total"] == 0


def test_cada_novela_devuelve_solo_lo_suyo(instancia: Instancia) -> None:
    a = instancia.cliente.post("/novelas", json=brief_ejemplo(destinatario__nombre="Ana")).json()
    b = instancia.cliente.post("/novelas", json=brief_ejemplo(destinatario__nombre="Bea")).json()
    assert (
        instancia.cliente.get(f"/novelas/{a['novel_id']}").json()["brief"]["destinatario"]["nombre"]
        == "Ana"
    )
    assert (
        instancia.cliente.get(f"/novelas/{b['novel_id']}").json()["brief"]["destinatario"]["nombre"]
        == "Bea"
    )
    db = _recursos(instancia).db
    palabras_a = db.ejecutar_sync(lambda con: palabras_de_novela(con, novel_id=a["novel_id"]))
    assert len(palabras_a) == len(brief_ejemplo()["palabras_prohibidas"])
