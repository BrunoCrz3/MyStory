"""H3 · pruebas 9, 13, 14 y 15 — RF-CANON-06, RF-CANON-09, RF-CANON-13, RF-CANON-14.

Las tres consultas de `consultar-canon` y la simulacion de retcon, que en v1
responde y no aplica.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.canon import service
from app.canon.models import EstadoDePromesa, TipoDeHecho
from app.commons import errores
from app.commons.db.conexion import Conexion
from app.novel.models import EstadoDeEscena
from tests.canon import fabrica

SIN_PLAZO = settings(max_examples=20, deadline=None)


# --- 13. Contradicciones --------------------------------------------------


def test_se_detecta_una_contradiccion_entre_dos_hechos_con_su_gravedad(
    base: Conexion,
) -> None:
    """RF-CANON-06. Es la entrada del ciclo contradiccion -> retcon -> invalidacion."""
    mundo = fabrica.mundo(base)
    primera = mundo.escena_consolidada(
        hechos=[mundo.hecho(TipoDeHecho.ESTADO_VITAL, sujeto=mundo.ilia, valor="muerto")]
    )
    segunda = mundo.escena_consolidada(
        hechos=[mundo.hecho(TipoDeHecho.UBICACION, sujeto=mundo.ilia, lugar=mundo.orilla)]
    )

    contradicciones = service.detectar_contradicciones(base)

    assert len(contradicciones) == 1
    unica = contradicciones[0]
    hechos = {unica.hecho_a_id, unica.hecho_b_id}
    assert hechos == {
        service.hechos_establecidos_en(base, primera)[0].id,
        service.hechos_establecidos_en(base, segunda)[0].id,
    }
    assert unica.tipo == "personaje_no_vivo_que_actua"
    assert unica.gravedad == "alta"


def test_dos_hechos_compatibles_no_producen_contradiccion(base: Conexion) -> None:
    mundo = fabrica.mundo(base)
    mundo.escena_consolidada(
        hechos=[mundo.hecho(TipoDeHecho.UBICACION, sujeto=mundo.ilia, lugar=mundo.vado)]
    )
    mundo.escena_consolidada(
        hechos=[mundo.hecho(TipoDeHecho.UBICACION, sujeto=mundo.ilia, lugar=mundo.orilla)]
    )
    assert service.detectar_contradicciones(base) == []


# --- 9. Promesas ----------------------------------------------------------


@SIN_PLAZO
@given(distancia=st.integers(min_value=1, max_value=3))
def test_una_promesa_pagada_tiene_escena_de_apertura_anterior(distancia: int) -> None:
    """P-45, RF-CANON-13.

    El punto ciego declarado se asume: exige el setup registrado, no que
    estuviera sembrado en el texto. Una promesa abierta y pagada en escenas
    contiguas cumple igual.
    """
    with fabrica.base_nueva() as base:
        mundo = fabrica.mundo(base, escenas=distancia + 2)
        apertura = mundo.escena_consolidada(hechos=[], promesas=["que el rio conteste"])
        promesa = service.promesas_abiertas_en(base, apertura)[0]

        for _ in range(distancia - 1):
            mundo.escena_consolidada(hechos=[])
        pago = mundo.escena_consolidada(hechos=[])

        pagada = service.transicionar_promesa(base, promesa.id, EstadoDePromesa.PAGADA, pago)
        assert pagada.estado is EstadoDePromesa.PAGADA
        assert service.escena_de_apertura(base, promesa.id) == apertura
        assert service.escena_de_pago(base, promesa.id) == pago
        assert service.promesas_abiertas_en(base, pago) == []


def test_una_promesa_no_se_puede_pagar_en_su_propia_escena_de_apertura(
    base: Conexion,
) -> None:
    mundo = fabrica.mundo(base)
    apertura = mundo.escena_consolidada(hechos=[], promesas=["que el rio conteste"])
    promesa = service.promesas_abiertas_en(base, apertura)[0]

    with pytest.raises(errores.PromesaPagadaAntesDeAbrirse):
        service.transicionar_promesa(base, promesa.id, EstadoDePromesa.PAGADA, apertura)


def test_pagar_una_promesa_sin_decir_en_que_escena_no_vale(base: Conexion) -> None:
    mundo = fabrica.mundo(base)
    apertura = mundo.escena_consolidada(hechos=[], promesas=["que el rio conteste"])
    promesa = service.promesas_abiertas_en(base, apertura)[0]

    with pytest.raises(errores.PromesaSinEscenaDePago):
        service.transicionar_promesa(base, promesa.id, EstadoDePromesa.PAGADA, None)


# --- 14. Estancamiento ----------------------------------------------------


def test_se_consultan_los_arcos_hilos_y_promesas_que_llevan_mas_escenas_sin_avanzar(
    base: Conexion,
) -> None:
    """P-44, RF-CANON-14, preguntas de competencia 6, 7 y 8.

    Los tres umbrales de `continuidad` estan en `null` y son [historico]. La
    consulta no falla por eso: mide, informa de que el umbral no esta declarado
    y deja la comparacion para cuando lo este. Es la misma politica que la fase
    de medicion — medir no es cerrar el paso (RF-QUA-05).
    """
    mundo = fabrica.mundo(base, escenas=6)
    arco = mundo.un_arco_que_avanza_en(0)
    hilo = mundo.un_hilo_que_avanza_en(0)
    apertura = mundo.escena_consolidada(hechos=[], promesas=["que el rio conteste"])
    for _ in range(4):
        mundo.escena_consolidada(hechos=[])

    informe = service.estancados(base)

    assert informe.umbrales_declarados is False
    porarco = {fila.id: fila for fila in informe.arcos}
    assert porarco[arco].escenas_sin_avanzar >= 4
    assert porarco[arco].supera_umbral is None

    assert {fila.id for fila in informe.hilos} == {hilo}
    assert [fila.id for fila in informe.promesas] == [
        service.promesas_abiertas_en(base, apertura)[0].id
    ]

    # Con umbral explicito si compara: la consulta sirve hoy y sirve mas.
    comparado = service.estancados(base, umbral_arco=2, umbral_hilo=2, umbral_promesa=2)
    assert comparado.umbrales_declarados is True
    assert {fila.id for fila in comparado.arcos if fila.supera_umbral} == {arco}


# --- 15. Retcon: v1 responde, no aplica -----------------------------------


def test_simular_un_retcon_no_marca_nada_obsoleto(base: Conexion) -> None:
    """RF-CANON-09, A-34, spec §1.3."""
    mundo = fabrica.mundo(base, escenas=5)
    primera = mundo.escena_consolidada(
        hechos=[mundo.hecho(TipoDeHecho.POSESION, sujeto=mundo.ilia, artefacto=mundo.llave)]
    )
    segunda = mundo.escena_consolidada(
        hechos=[mundo.hecho(TipoDeHecho.POSESION, sujeto=mundo.baro, artefacto=mundo.llave)]
    )
    ajena = mundo.escena_consolidada(
        hechos=[mundo.hecho(TipoDeHecho.DESCRIPTIVO, sujeto=mundo.baro, valor="llueve")]
    )

    hecho = service.hechos_establecidos_en(base, primera)[0]
    simulacion = service.simular_retcon(base, hecho.id)

    assert simulacion.hecho_id == hecho.id
    assert set(simulacion.escenas_invalidadas) == {primera, segunda}
    assert ajena not in simulacion.escenas_invalidadas

    # Nada cambia: v1 responde y no aplica.
    for escena in (primera, segunda, ajena):
        assert service.estado_de_escena(base, escena) is EstadoDeEscena.ACEPTADA
    assert service.inventario_del_canon(base)["retcon"] == 0
