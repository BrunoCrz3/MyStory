"""Lectura por versión: historial, versión con su índice y capítulos (RF-VER-01, RF-VER-02,
RF-VER-03, RF-NOVEL-05)."""

from __future__ import annotations

import uuid

from tests.conftest import Instancia, ValidarContrato
from tests.dobles.guiones import guion_completo
from tests.fixtures.briefs import brief_ejemplo
from tests.process.test_orquestador import esperar


def _publicada(i: Instancia) -> str:
    guion_completo(i.modelo)
    novela = i.cliente.post("/novelas", json=brief_ejemplo()).json()["novel_id"]
    gid = i.cliente.post(f"/novelas/{novela}/generaciones").json()["generacion_id"]
    g = esperar(i.cliente, novela, gid, lambda g: g["es_terminal"])
    assert g["estado"] == "Publicada", g
    assert g["version_resultante"] == 1
    return str(novela)


def test_historial_indice_y_capitulos_de_la_version_1(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    c = instancia.cliente
    novela = _publicada(instancia)

    r = c.get(f"/novelas/{novela}/versiones")
    validar_contra_contrato(r, "listarVersiones")
    assert r.status_code == 200
    [resumen] = r.json()
    assert resumen["version"] == 1
    assert resumen["version_anterior"] is None
    assert resumen["capitulos_modificados"] == []

    r = c.get(f"/novelas/{novela}/versiones/1")
    validar_contra_contrato(r, "obtenerVersion")
    v = r.json()
    assert v["novel_id"] == novela and v["titulo"] == "El verano del Alondra"
    assert len(v["hash"]) == 64
    assert v["dedicatoria"] == brief_ejemplo()["dedicatoria"]
    assert [x["numero"] for x in v["capitulos"]] == list(range(1, 11))
    assert all(x["modificado"] is False and x["titulo"] for x in v["capitulos"])

    r = c.get(f"/novelas/{novela}/versiones/1/capitulos")
    validar_contra_contrato(r, "listarCapitulos")
    capitulos = r.json()
    assert [x["numero"] for x in capitulos] == list(range(1, 11))
    for x in capitulos:
        assert x["estado"] == "Aceptado" and x["modificado"] is False
        assert x["texto"] and x["palabras"] > 0 and x["resumen"] and x["gancho_cierre"]
        assert x["pov"] and x["lugar"] and x["funcion_dramatica"]

    r = c.get(f"/novelas/{novela}/versiones/1/capitulos/3")
    validar_contra_contrato(r, "obtenerCapitulo")
    assert r.json() == capitulos[2]

    assert c.get(f"/novelas/{novela}").json()["version_vigente"] == 1


def test_errores_de_lectura(instancia: Instancia, validar_contra_contrato: ValidarContrato) -> None:
    c = instancia.cliente
    novela = _publicada(instancia)
    casos = [
        (f"/novelas/{novela}/versiones/2", "obtenerVersion", "version-no-encontrada"),
        (f"/novelas/{novela}/versiones/2/capitulos", "listarCapitulos", "version-no-encontrada"),
        (
            f"/novelas/{novela}/versiones/1/capitulos/11",
            "obtenerCapitulo",
            "version-no-encontrada",
        ),
        (f"/novelas/{uuid.uuid4()}/versiones", "listarVersiones", "novela-no-encontrada"),
        (f"/novelas/{uuid.uuid4()}/versiones/1", "obtenerVersion", "novela-no-encontrada"),
    ]
    for ruta, operacion, tipo in casos:
        r = c.get(ruta)
        validar_contra_contrato(r, operacion)
        assert r.status_code == 404, ruta
        assert r.json()["type"] == f"/problemas/{tipo}", ruta


def test_una_novela_sin_publicar_no_tiene_versiones(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    c = instancia.cliente
    novela = c.post("/novelas", json=brief_ejemplo()).json()["novel_id"]
    r = c.get(f"/novelas/{novela}/versiones")
    validar_contra_contrato(r, "listarVersiones")
    assert r.json() == []
    assert c.get(f"/novelas/{novela}/versiones/1").status_code == 404
