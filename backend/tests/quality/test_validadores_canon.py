"""Hook de capítulo contra el canon: `consistencia_factica` (mitad programática),
`cumplimiento_brief` y `reglas_mundo` (RF-QUA-02; O-26, O-27, O-29, O-30, O-42).

Un defecto inyectado por validador y un capítulo limpio que pasa los tres.
"""

from __future__ import annotations

import pytest

from app.commons.config import cargar_config
from app.quality.registro import comprobar
from app.quality.validadores.canon import (
    EntidadPrevista,
    consistencia_factica,
    cumplimiento_brief,
    numero_en_texto,
    reglas_mundo,
)
from tests.arquitectura.comprobadores import RAIZ_REPO
from tests.fixtures.borradores import prosa

CONFIG = cargar_config(RAIZ_REPO / "config")
NOMBRES = ["Ondina", "Tomás", "el puerto", "el faro"]
HECHOS = ["Ondina tiene 34 años y vive lejos del mar.", "Tomás arregla barcas en el puerto."]
REGLAS = ["El abuelo nunca aparece", "Nada de violencia"]
ALCANCE = [{"tipo": "personaje", "nombre": "Ondina"}, {"tipo": "lugar", "nombre": "el puerto"}]
LIMPIO = prosa(
    1200,
    extra="Ondina, que tiene treinta y cuatro años, bajó al puerto a buscar a Tomás. "
    "Cuando tenía doce años había aprendido allí a navegar.",
)


def test_numeros_en_letra_y_en_cifra() -> None:
    assert numero_en_texto("34") == 34
    assert numero_en_texto("treinta y cuatro") == 34
    assert numero_en_texto("cuarenta") == 40
    assert numero_en_texto("veintidós") == 22
    assert numero_en_texto("doce") == 12
    assert numero_en_texto("muchos") is None


def test_un_capitulo_limpio_pasa_los_tres() -> None:
    resultados = [
        consistencia_factica(CONFIG, LIMPIO, hechos=HECHOS, nombres=NOMBRES),
        cumplimiento_brief(CONFIG, LIMPIO, alcance=ALCANCE, previstas=[]),
        reglas_mundo(LIMPIO, reglas=REGLAS),
    ]
    for r in resultados:
        comprobar(r)
        assert r.pasa and r.valor == 1.0 and r.defectos == [], (r.nombre, r.detalle)


def test_una_edad_que_contradice_un_hecho_adoptado_es_un_defecto() -> None:
    texto = prosa(1200, extra="Ondina, que tiene cuarenta años, bajó al puerto.")
    r = consistencia_factica(CONFIG, texto, hechos=HECHOS, nombres=NOMBRES)
    assert not r.pasa and r.valor == 0.0
    [defecto] = r.defectos
    assert defecto.dimension == "consistencia_factica"
    assert "40" in defecto.descripcion and "34" in defecto.descripcion
    assert defecto.gravedad == "alta"


def test_la_edad_en_pasado_no_contradice_la_del_presente() -> None:
    texto = prosa(1200, extra="Cuando Ondina tenía doce años, cumplía los veranos en el faro.")
    assert consistencia_factica(CONFIG, texto, hechos=HECHOS, nombres=NOMBRES).pasa


def test_el_umbral_y_el_cierre_salen_de_config() -> None:
    texto = prosa(1200, extra="Ondina, que tiene cuarenta años, bajó al puerto.")
    r = consistencia_factica(CONFIG, texto, hechos=HECHOS, nombres=NOMBRES)
    # Con score: cierra el paso solo fuera de la fase de medición (A-03).
    assert r.cierra_el_paso is CONFIG.umbrales.medicion.cerrar_el_paso


def test_una_regla_del_mundo_violada_es_un_defecto_que_cierra_el_paso() -> None:
    texto = prosa(1200, extra="El abuelo de Ondina la esperaba en el muelle.")
    r = reglas_mundo(texto, reglas=REGLAS)
    assert not r.pasa and r.cierra_el_paso
    [defecto] = r.defectos
    assert "abuelo" in defecto.descripcion and defecto.gravedad == "alta"
    # La regla de forma no es una consulta: se declara como no comprobable, no suspende.
    assert "Nada de violencia" in r.detalle


@pytest.mark.parametrize(
    "regla", ["El abuelo nunca aparece", "No aparece el abuelo", "Los abuelos no aparecen"]
)
def test_las_formas_de_la_regla_de_exclusion(regla: str) -> None:
    texto = prosa(1200, extra="Sus abuelos vivían en la otra orilla.")
    assert not reglas_mundo(texto, reglas=[regla]).pasa


def test_una_restriccion_de_destino_incumplida_es_un_defecto() -> None:
    alcance = [*ALCANCE, {"tipo": "lugar", "nombre": "el faro"}]
    texto = prosa(1200, extra="Ondina bajó al puerto a buscar a Tomás.")
    r = cumplimiento_brief(CONFIG, texto, alcance=alcance, previstas=[])
    assert not r.pasa
    assert r.valor == pytest.approx(2 / 3)
    [defecto] = r.defectos
    assert "el faro" in defecto.descripcion


def test_adelantar_a_quien_el_plan_presenta_despues_es_un_defecto() -> None:
    previstas = [EntidadPrevista(nombre="Tomás", capitulo=7)]
    r = cumplimiento_brief(CONFIG, LIMPIO, alcance=ALCANCE, previstas=previstas)
    assert not r.pasa
    assert any("capítulo 7" in d.descripcion for d in r.defectos)
