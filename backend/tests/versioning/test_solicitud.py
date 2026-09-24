"""Solicitud de cambio por hecho y análisis de impacto (RF-VER-06, RF-VER-09).

Crear la solicitud **no regenera nada**: calcula los capítulos que **usan** el hecho —no solo
el que lo estableció— y los devuelve para que el lector confirme.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from tests.canon.test_hechos_por_version import publicada_con_uso
from tests.conftest import Instancia, ValidarContrato


def _hecho_del_dos(i: Instancia, novela: str) -> dict[str, Any]:
    hechos = i.cliente.get(f"/novelas/{novela}/versiones/1/hechos").json()
    return next(h for h in hechos if h["capitulo_establece"] == 2)


def _crear(i: Instancia, novela: str, cuerpo: dict[str, Any]) -> Any:
    return i.cliente.post(f"/novelas/{novela}/solicitudes-cambio", json=cuerpo)


def test_el_analisis_de_impacto_va_sobre_usa_y_no_regenera(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    novela = publicada_con_uso(instancia)
    hecho = _hecho_del_dos(instancia, novela)
    llamadas = dict(instancia.modelo.llamadas)
    recursos = instancia.app.state.recursos
    trabajos = recursos.db.ejecutar_sync(
        lambda con: con.execute("SELECT COUNT(*) FROM trabajo").fetchone()[0]
    )

    r = _crear(
        instancia,
        novela,
        {
            "hecho_id": hecho["hecho_id"],
            "enunciado_nuevo": "El perro se llama Nala",
            "capitulo_origen": 7,
        },
    )
    validar_contra_contrato(r, "crearSolicitudCambio")
    assert r.status_code == 201, r.text
    solicitud = r.json()
    assert solicitud["estado"] == "pendiente-de-confirmacion"
    assert solicitud["analisis_impacto"]["capitulos_afectados"] == [2, 7]
    assert solicitud["hecho_afectado"]["hecho_id"] == hecho["hecho_id"]
    assert solicitud["version_resultante"] is None
    assert solicitud["enunciado_nuevo"] == "El perro se llama Nala"
    # Los hechos que establecen los capítulos afectados quedan señalados como derivados.
    assert hecho["hecho_id"] not in solicitud["analisis_impacto"]["hechos_derivados"]
    assert len(solicitud["analisis_impacto"]["hechos_derivados"]) == 1

    assert dict(instancia.modelo.llamadas) == llamadas
    assert (
        recursos.db.ejecutar_sync(
            lambda con: con.execute("SELECT COUNT(*) FROM trabajo").fetchone()[0]
        )
        == trabajos
    )

    r = instancia.cliente.get(f"/novelas/{novela}/solicitudes-cambio/{solicitud['solicitud_id']}")
    validar_contra_contrato(r, "obtenerSolicitudCambio")
    assert r.status_code == 200 and r.json() == solicitud


def test_con_una_generacion_viva_es_409(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    novela = publicada_con_uso(instancia)
    hecho = _hecho_del_dos(instancia, novela)
    recursos = instancia.app.state.recursos
    recursos.db.en_transaccion_sync(
        lambda con: con.execute(
            "INSERT INTO trabajo (id, novel_id, tipo, estado_cola, estado, version_objetivo,"
            " estimacion, iniciada_en) VALUES (?, ?, 'inicial', 'en-curso', 'Escribiendo', 2,"
            " 1000, '2026-01-01T00:00:00Z')",
            (str(uuid.uuid4()), novela),
        )
    )
    r = _crear(
        instancia,
        novela,
        {"hecho_id": hecho["hecho_id"], "enunciado_nuevo": "x", "capitulo_origen": 2},
    )
    validar_contra_contrato(r, "crearSolicitudCambio")
    assert r.status_code == 409 and r.json()["type"] == "/problemas/generacion-en-curso"


def test_lo_que_no_existe_es_404(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    novela = publicada_con_uso(instancia)
    cuerpo = {"hecho_id": str(uuid.uuid4()), "enunciado_nuevo": "x", "capitulo_origen": 1}
    r = _crear(instancia, novela, cuerpo)
    validar_contra_contrato(r, "crearSolicitudCambio")
    assert r.status_code == 404 and r.json()["type"] == "/problemas/hecho-no-encontrado"

    r = _crear(instancia, str(uuid.uuid4()), cuerpo)
    assert r.status_code == 404 and r.json()["type"] == "/problemas/novela-no-encontrada"

    r = instancia.cliente.get(f"/novelas/{novela}/solicitudes-cambio/{uuid.uuid4()}")
    validar_contra_contrato(r, "obtenerSolicitudCambio")
    assert r.status_code == 404


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"enunciado_nuevo": "x", "capitulo_origen": 1},
        {
            "hecho_id": str(uuid.uuid4()),
            "fragmento": "algo",
            "enunciado_nuevo": "x",
            "capitulo_origen": 1,
        },
        {"hecho_id": str(uuid.uuid4()), "enunciado_nuevo": "", "capitulo_origen": 1},
    ],
)
def test_exactamente_uno_de_hecho_o_fragmento(
    cuerpo: dict[str, Any], instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    novela = publicada_con_uso(instancia)
    r = _crear(instancia, novela, cuerpo)
    validar_contra_contrato(r, "crearSolicitudCambio")
    assert r.status_code == 422
