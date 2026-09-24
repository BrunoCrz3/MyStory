"""Guardrail de palabras prohibidas: normalización a los dos lados y tres niveles
(RF-GUARD-01, RF-GUARD-02; filas O-05, O-06, O-08)."""

from __future__ import annotations

import pytest

from app.commons.config import cargar_config
from app.commons.config.modelos import Normalizacion
from app.guardrail.service import Guardrail, PerfilLector
from tests.arquitectura.comprobadores import RAIZ_REPO

CONFIG = cargar_config(RAIZ_REPO / "config")
TODAS = CONFIG.umbrales.guardrail.normalizacion
ADULTO = PerfilLector(edad=34, ocasion="cumpleanos")


def _guardrail(**apagadas: bool) -> Guardrail:
    reglas = Normalizacion(**{**TODAS.model_dump(), **apagadas})
    return Guardrail(CONFIG, normalizacion=reglas)


def _formas(
    g: Guardrail, texto: str, novela: list[str], perfil: PerfilLector = ADULTO
) -> list[str]:
    return [c.palabra for c in g.comprobar(texto, palabras_novela=novela, perfil=perfil)]


def test_acento_y_plural_se_normalizan() -> None:
    assert _formas(_guardrail(), "Qué par de Imbeciles.", ["imbécil"]) == ["imbécil"]


def test_signos_intercalados() -> None:
    assert _formas(_guardrail(), "Eres una i-d-i-o-t-a, dijo.", ["idiota"]) == ["idiota"]


def test_diminutivo_regular() -> None:
    assert _formas(_guardrail(), "Mi idiotita favorita.", ["idiota"]) == ["idiota"]


def test_mayusculas() -> None:
    assert _formas(_guardrail(), "IDIOTA.", ["idiota"]) == ["idiota"]


@pytest.mark.parametrize(
    ("apagada", "texto", "palabra"),
    [
        ("minusculas", "Idiota", "idiota"),
        ("quitar_acentos", "imbecil", "imbécil"),
        ("quitar_signos", "i-d-i-o-t-a", "idiota"),
        ("plurales", "imbeciles", "imbecil"),
        ("variantes_simples", "idiotita", "idiota"),
    ],
)
def test_cada_transformacion_apagada_deja_pasar_su_variante(
    apagada: str, texto: str, palabra: str
) -> None:
    """Prueba que las cinco están activas y no solo una."""
    assert _formas(_guardrail(), texto, [palabra]) == [palabra]
    assert _formas(_guardrail(**{apagada: False}), texto, [palabra]) == []


def test_la_normalizacion_se_aplica_a_la_palabra_tambien() -> None:
    assert _formas(_guardrail(), "un imbécil", ["IMBECILES"]) == ["IMBECILES"]


def test_no_hay_falsos_positivos_por_subcadena() -> None:
    assert _formas(_guardrail(), "Luisa llegó tarde.", ["Luis"]) == []
    assert _formas(_guardrail(), "Luis llegó tarde.", ["Luis"]) == ["Luis"]


def test_nivel_global_sin_que_nadie_lo_declare() -> None:
    coincidencias = _guardrail().comprobar("Menudo imbécil.", palabras_novela=[], perfil=ADULTO)
    assert [c.nivel for c in coincidencias] == ["global"]


def test_nivel_perfil_depende_de_la_edad() -> None:
    texto = "Brindaron con cerveza."
    infantil = PerfilLector(edad=7, ocasion="cumpleanos")
    assert _guardrail().comprobar(texto, palabras_novela=[], perfil=ADULTO) == []
    assert [
        c.nivel for c in _guardrail().comprobar(texto, palabras_novela=[], perfil=infantil)
    ] == ["perfil"]


def test_nivel_perfil_depende_de_la_ocasion() -> None:
    texto = "Hablaron del divorcio."
    boda = PerfilLector(edad=34, ocasion="boda")
    assert _guardrail().comprobar(texto, palabras_novela=[], perfil=ADULTO) == []
    assert [c.nivel for c in _guardrail().comprobar(texto, palabras_novela=[], perfil=boda)] == [
        "perfil"
    ]


def test_nivel_novela_y_gana_el_mas_restrictivo() -> None:
    texto = "Luis, el imbécil."
    coincidencias = _guardrail().comprobar(
        texto, palabras_novela=["Luis", "imbécil"], perfil=ADULTO
    )
    niveles = {c.palabra.lower(): c.nivel for c in coincidencias}
    assert niveles == {"luis": "novela", "imbécil": "novela"}


def test_la_coincidencia_lleva_posicion_en_el_texto_original() -> None:
    texto = "Al fondo, un Imbécil."
    (c,) = _guardrail().comprobar(texto, palabras_novela=[], perfil=ADULTO)
    assert texto[c.inicio : c.fin] == "Imbécil"


def test_expresion_de_varias_palabras() -> None:
    assert _formas(_guardrail(), "Aquel viejo verde sonrió.", ["viejo verde"]) == ["viejo verde"]
    assert _formas(_guardrail(), "Un viejo y verde árbol.", ["viejo verde"]) == []
