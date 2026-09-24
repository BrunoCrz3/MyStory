"""Solicitud por fragmento: el sistema propone un hecho candidato y espera confirmación
(RF-VER-07, TO-011, D-19). Ninguno de los dos casos regenera nada."""

from __future__ import annotations

from typing import Any

from app.commons.config import cargar_config
from app.versioning.candidato import similitud
from tests.canon.test_hechos_por_version import publicada_con_uso
from tests.conftest import Instancia, ValidarContrato


def test_la_similitud_es_jaccard_sobre_tokens_normalizados() -> None:
    assert similitud("El perro se llamaba Luna.", "el PERRO se llamaba luna") == 1.0
    assert similitud("Luna corría", "Nala dormía") == 0.0
    assert 0 < similitud("el perro Luna corría", "el perro Nala corría") < 1


def test_el_umbral_sale_de_config_y_es_provisional() -> None:
    assert 0 < cargar_config().umbrales.regeneracion.similitud_hecho_candidato <= 1


def _hechos(i: Instancia, novela: str) -> list[dict[str, Any]]:
    return list(i.cliente.get(f"/novelas/{novela}/versiones/1/hechos").json())


def test_un_fragmento_del_soporte_propone_ese_hecho_sin_regenerar(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    novela = publicada_con_uso(instancia)
    del_dos = next(h for h in _hechos(instancia, novela) if h["capitulo_establece"] == 2)
    llamadas = dict(instancia.modelo.llamadas)

    r = instancia.cliente.post(
        f"/novelas/{novela}/solicitudes-cambio",
        json={
            "fragmento": del_dos["fragmento_soporte"],
            "enunciado_nuevo": "El perro se llama Nala",
            "capitulo_origen": 7,
        },
    )
    validar_contra_contrato(r, "crearSolicitudCambio")
    assert r.status_code == 201, r.text
    solicitud = r.json()
    assert solicitud["estado"] == "pendiente-de-confirmacion"
    assert solicitud["hecho_candidato"] == del_dos["enunciado"]
    assert "hecho_afectado" not in solicitud
    assert solicitud["analisis_impacto"]["capitulos_afectados"] == [2, 7]
    assert dict(instancia.modelo.llamadas) == llamadas


def test_un_fragmento_sin_candidato_no_propone_nada(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    novela = publicada_con_uso(instancia)
    r = instancia.cliente.post(
        f"/novelas/{novela}/solicitudes-cambio",
        json={
            "fragmento": "Una frase que no sostiene ningún hecho de este capítulo.",
            "enunciado_nuevo": "Otra cosa",
            "capitulo_origen": 7,
        },
    )
    validar_contra_contrato(r, "crearSolicitudCambio")
    solicitud = r.json()
    assert solicitud["estado"] == "pendiente-de-confirmacion"
    assert solicitud["hecho_candidato"] is None
    assert "analisis_impacto" not in solicitud
