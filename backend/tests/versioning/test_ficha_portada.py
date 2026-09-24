"""Ficha y portada de una versión (RF-VER-04, RF-VER-05): la ficha sale de la story bible de
**esa** versión, con los capítulos donde aparece cada personaje y lugar; la portada lleva la
dedicatoria del brief."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.commons.llm import Peticion
from app.versioning import confirmar
from app.versioning import service as versioning
from tests.canon.test_hechos_por_version import publicada_con_uso
from tests.conftest import Entorno, Instancia, ValidarContrato
from tests.dobles.guiones import capitulo_aceptado_de, numero_de_la_tarea, redactar
from tests.fixtures.borradores import borrador
from tests.fixtures.briefs import brief_ejemplo
from tests.fixtures.extracciones import extraccion
from tests.versioning.test_confirmar import _publicada, _solicitud

NUEVO = "El perro se llama Nala"


def test_ficha_y_portada_por_http(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    novela = publicada_con_uso(instancia)
    r = instancia.cliente.get(f"/novelas/{novela}/versiones/1/ficha")
    validar_contra_contrato(r, "obtenerFicha")
    ficha = r.json()
    marta = next(p for p in ficha["personajes"] if p["nombre"] == "Marta")
    assert marta["capitulos"] == list(range(1, 11)) and marta["descripcion"]
    puerto = next(lugar for lugar in ficha["lugares"] if lugar["nombre"] == "el puerto")
    assert puerto["capitulos"] and all(1 <= n <= 10 for n in puerto["capitulos"])
    assert {p["nombre"] for p in ficha["personajes"]} >= {"Marta", "Tomás"}

    r = instancia.cliente.get(f"/novelas/{novela}/versiones/1/portada")
    validar_contra_contrato(r, "obtenerPortada")
    portada = r.json()
    assert portada["dedicatoria"] == brief_ejemplo()["dedicatoria"]
    assert portada["titulo"] == "El verano del Alondra"
    assert portada["destinatario"] == "Marta" and portada["ocasion"] == "cumpleaños"

    for sufijo in ("ficha", "portada"):
        r = instancia.cliente.get(f"/novelas/{novela}/versiones/9/{sufijo}")
        assert r.status_code == 404 and r.json()["type"] == "/problemas/version-no-encontrada"
        r = instancia.cliente.get(f"/novelas/{uuid.uuid4()}/versiones/1/{sufijo}")
        assert r.status_code == 404


def _extractor_con_tomas(p: Peticion) -> dict[str, Any]:
    salida = extraccion(capitulo_aceptado_de(p))
    salida["eventos"][0]["personajes"] = ["Marta", "Tomás"]
    salida["personajes_presentes"] = ["Marta", "Tomás"]
    return salida


def _redactor(p: Peticion) -> dict[str, str]:
    if NUEVO in p.mensajes[0].contenido:
        n = numero_de_la_tarea(p)
        return borrador(titulo=f"Capítulo {n}: Nala", extra=f"{NUEVO}. Tomás la esperaba.")
    return redactar(p)


@pytest.mark.anyio
async def test_la_ficha_de_cada_version_sale_de_su_story_bible(entorno: Entorno) -> None:
    novela = await _publicada(entorno)
    sid, _ = await _solicitud(entorno, novela)
    entorno.modelo.por_defecto["redactor"] = _redactor
    entorno.modelo.por_defecto["extractor"] = _extractor_con_tomas
    g = await confirmar.confirmar(entorno.recursos, novela, sid)
    await entorno.orquestador().ejecutar(str(g.generacion_id))

    v1 = await versioning.obtener_ficha(entorno.recursos.db, novela, 1)
    v2 = await versioning.obtener_ficha(entorno.recursos.db, novela, 2)
    tomas_v1 = next(p for p in v1.personajes if p.nombre == "Tomás")
    tomas_v2 = next(p for p in v2.personajes if p.nombre == "Tomás")
    assert 2 not in tomas_v1.capitulos and 7 not in tomas_v1.capitulos
    assert {2, 7} <= set(tomas_v2.capitulos)
