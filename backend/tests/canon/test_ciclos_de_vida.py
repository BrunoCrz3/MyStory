"""H3 · pruebas 5 y 6 — A-30, A-31, A-33, RF-CANON-02, RF-CANON-05, RF-CANON-10.

Model checking sobre las dos maquinas, con el producto cartesiano entero, igual
que en H2. Los diagramas estan escritos a mano aqui: leerlos de la constante que
implementa el codigo solo diria que la constante es igual a si misma.

El punto ciego que `verification.md` anota en A-33 se asume y no se cierra: se
impide la transicion de salida, no la creacion de un hecho nuevo identico al
refutado. Lo que si se exige es que el sucesor referencie al anterior.
"""

from __future__ import annotations

import itertools

import pytest

from app.canon import service
from app.canon.models import (
    TRANSICIONES_DE_LA_PROMESA,
    TRANSICIONES_DEL_HECHO,
    EstadoDePromesa,
    EstatusDeHecho,
)
from app.commons import errores
from app.commons.db.conexion import Conexion
from tests.canon import fabrica

# docs/domain-knowledge.md § Ciclo de vida de un hecho canonico
DIAGRAMA_DEL_HECHO = {
    ("provisional", "confirmado"),
    ("provisional", "implicito"),
    ("implicito", "confirmado"),
    ("confirmado", "retconeado"),
    ("confirmado", "refutado"),
    ("retconeado", "confirmado"),
}

# docs/domain-knowledge.md § Ciclo de vida de una promesa narrativa
DIAGRAMA_DE_LA_PROMESA = {
    ("pendiente", "pagada"),
    ("pendiente", "subvertida"),
    ("pendiente", "rota"),
}

CON_PAGO = {EstadoDePromesa.PAGADA, EstadoDePromesa.SUBVERTIDA}


def test_los_cinco_valores_de_estatus_de_hecho_son_los_de_la_ontologia() -> None:
    """Con `implicito` y sin `descartado` (spec §7)."""
    assert {estatus.value for estatus in EstatusDeHecho} == {
        "confirmado",
        "implicito",
        "provisional",
        "retconeado",
        "refutado",
    }


def test_los_cuatro_valores_de_estado_de_promesa_son_los_de_la_ontologia() -> None:
    assert {estado.value for estado in EstadoDePromesa} == {
        "pendiente",
        "pagada",
        "rota",
        "subvertida",
    }


def test_el_ciclo_de_vida_del_hecho_no_admite_transiciones_extra(base: Conexion) -> None:
    """A-30, RF-CANON-02."""
    declaradas = {
        (origen.value, destino.value)
        for origen, destinos in TRANSICIONES_DEL_HECHO.items()
        for destino in destinos
    }
    assert declaradas == DIAGRAMA_DEL_HECHO

    mundo = fabrica.mundo(base)
    for origen, destino in itertools.product(EstatusDeHecho, repeat=2):
        hecho_id = mundo.hecho_en(origen)
        par = (origen.value, destino.value)
        if par in DIAGRAMA_DEL_HECHO:
            assert service.transicionar_hecho(base, hecho_id, destino).estatus is destino
        else:
            with pytest.raises(errores.TransicionInvalida):
                service.transicionar_hecho(base, hecho_id, destino)
            assert service.obtener_hecho(base, hecho_id).estatus is origen


def test_el_ciclo_de_vida_de_la_promesa_no_admite_transiciones_extra(
    base: Conexion,
) -> None:
    """A-31, RF-CANON-05."""
    declaradas = {
        (origen.value, destino.value)
        for origen, destinos in TRANSICIONES_DE_LA_PROMESA.items()
        for destino in destinos
    }
    assert declaradas == DIAGRAMA_DE_LA_PROMESA

    mundo = fabrica.mundo(base)
    for origen, destino in itertools.product(EstadoDePromesa, repeat=2):
        promesa_id, pago = mundo.promesa_en(origen)
        par = (origen.value, destino.value)
        argumento = pago if destino in CON_PAGO else None
        if par in DIAGRAMA_DE_LA_PROMESA:
            resultado = service.transicionar_promesa(base, promesa_id, destino, argumento)
            assert resultado.estado is destino
        else:
            with pytest.raises(errores.TransicionInvalida):
                service.transicionar_promesa(base, promesa_id, destino, argumento)
            assert service.obtener_promesa(base, promesa_id).estado is origen


def test_refutado_y_rota_no_tienen_transicion_de_salida(base: Conexion) -> None:
    """A-33, RF-CANON-10. Son sumideros por diseno, no por olvido."""
    assert TRANSICIONES_DEL_HECHO[EstatusDeHecho.REFUTADO] == frozenset()
    assert TRANSICIONES_DE_LA_PROMESA[EstadoDePromesa.ROTA] == frozenset()

    mundo = fabrica.mundo(base)
    refutado = mundo.hecho_en(EstatusDeHecho.REFUTADO)
    for destino in EstatusDeHecho:
        with pytest.raises(errores.TransicionInvalida):
            service.transicionar_hecho(base, refutado, destino)

    rota, pago = mundo.promesa_en(EstadoDePromesa.ROTA)
    for destino in EstadoDePromesa:
        with pytest.raises(errores.TransicionInvalida):
            service.transicionar_promesa(base, rota, destino, pago)


def test_si_la_trama_vuelve_sobre_un_hecho_refutado_se_crea_otro_que_lo_referencia(
    base: Conexion,
) -> None:
    """RF-CANON-10: «se crea una entidad nueva que referencia a la anterior».

    Y se crea por donde se crea todo el canon: consolidando una escena aceptada.
    No hay una puerta lateral para resucitar un sumidero.
    """
    mundo = fabrica.mundo(base)
    refutado = mundo.hecho_en(EstatusDeHecho.REFUTADO)

    sucesor = mundo.hecho_nuevo(sucede_a_hecho_id=refutado)

    assert sucesor.sucede_a_hecho_id == refutado
    assert service.obtener_hecho(base, refutado).estatus is EstatusDeHecho.REFUTADO
