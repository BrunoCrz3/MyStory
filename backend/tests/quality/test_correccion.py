"""H5 · pruebas 8 y 9 — A-49, A-50, RF-QUA-07, RF-QUA-08.

La ruta de un defecto: se corrige, se revalida entero y se comprueba que la
correccion no ha roto nada que ya estaba bien. Parchear un eje y volver a mirar
solo ese eje es como no haber mirado.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from app.commons.db.conexion import Conexion
from app.quality import service as calidad
from tests.quality import fabrica

SIN_PLAZO = settings(max_examples=15, deadline=None)


def test_tras_corregir_se_reejecutan_todos_los_validadores(base: Conexion) -> None:
    """A-49, RF-QUA-07.

    La garantia es estructural: hay un registro unico de validadores y el unico
    camino que produce un informe lo recorre entero. No hay una via que revalide
    «solo lo que fallo», asi que no hay nada que olvidar.

    El punto ciego declarado se asume: garantiza que se invoquen todos, no que
    cada uno reciba el texto corregido en vez de una puntuacion en cache.
    """
    mundo = fabrica.mundo_criticable(base)
    mundo.declarar_voz_narrativa(persona="tercera", tiempo_verbal="pasado")
    umbrales = fabrica.umbrales()

    roto = calidad.criticar(
        base, umbrales, fabrica.peticion(mundo, texto="Cruce el vado. Yo sabia el precio.")
    )
    corregido = calidad.criticar(
        base,
        umbrales,
        fabrica.peticion(
            mundo, texto="Ilia cruzo el vado. Sabia el precio y no dijo nada.", version=2
        ),
    )

    declaradas = set(umbrales.calidad.model_dump())
    for informe in (roto, corregido):
        assert {p.dimension for p in informe.puntuaciones} == declaradas

    assert len(corregido.defectos) < len(roto.defectos)


@SIN_PLAZO
@given(version=st.integers(min_value=2, max_value=6))
def test_ninguna_correccion_empeora_una_dimension_que_ya_pasaba(version: int) -> None:
    """A-50, RF-QUA-08. Se compara contra el historial de `Version`.

    El punto ciego declarado se asume y pesa: compara puntuaciones, y ninguna
    esta calibrada. Dos valores igual de arbitrarios no dicen si la escena
    mejoro; lo que si dicen es si la correccion movio hacia abajo algo que antes
    estaba mas arriba, y eso es lo que se detecta.
    """
    with fabrica.base_nueva() as base:
        mundo = fabrica.mundo_criticable(base)
        umbrales = fabrica.umbrales()

        limpio = "Ilia cruzo el vado. Sabia el precio y no dijo nada. La puerta cedio."
        calidad.criticar(base, umbrales, fabrica.peticion(mundo, texto=limpio, version=1))

        empeorado = limpio + " " + ("Y entonces fue y entonces vino y entonces callo. " * 30)
        calidad.criticar(base, umbrales, fabrica.peticion(mundo, texto=empeorado, version=version))

        regresiones = calidad.comparar_con_anterior(base, mundo.escena_id, version)

        assert regresiones, "empeorar la prosa tiene que verse"
        for regresion in regresiones:
            assert regresion.valor_nuevo < regresion.valor_anterior
            assert regresion.dimension in set(umbrales.calidad.model_dump())


def test_una_correccion_que_solo_mejora_no_produce_regresiones(base: Conexion) -> None:
    mundo = fabrica.mundo_criticable(base)
    umbrales = fabrica.umbrales()

    pobre = "Y entonces fue y entonces vino y entonces callo. " * 20
    calidad.criticar(base, umbrales, fabrica.peticion(mundo, texto=pobre, version=1))
    calidad.criticar(
        base,
        umbrales,
        fabrica.peticion(
            mundo,
            texto="Ilia cruzo el vado, pero la puerta ya estaba abierta; por tanto entro.",
            version=2,
        ),
    )

    assert calidad.comparar_con_anterior(base, mundo.escena_id, 2) == []


def test_sin_informe_anterior_no_hay_nada_que_comparar(base: Conexion) -> None:
    mundo = fabrica.mundo_criticable(base)
    calidad.criticar(base, fabrica.umbrales(), fabrica.peticion(mundo, version=1))

    assert calidad.comparar_con_anterior(base, mundo.escena_id, 1) == []
