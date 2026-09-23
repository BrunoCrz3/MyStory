"""H2 · prueba 1 — A-29, RF-NOVEL-04.

Model checking sobre los cinco estados: se recorre el producto cartesiano
entero, no una muestra. Una prueba que solo ejercita las transiciones buenas
deja pasar las malas, y aqui lo que importa es justo lo que **no** se puede
hacer.

Cada origen se alcanza caminando por el diagrama, nunca escribiendo el estado a
mano. Una puerta trasera para colocar la escena donde conviene seria codigo de
produccion que solo existe para las pruebas, y eso es lo que veta la regla 8.

La extraccion no es un estado. Es el paso que sigue a `aceptada`, y meterla en
la enumeracion convertiria un paso del proceso en estado del dominio.
"""

import itertools

import pytest

from app.commons import errores
from app.commons.db.conexion import Conexion
from app.novel import service
from app.novel.models import TRANSICIONES, EstadoDeEscena
from tests.novel.fabrica import ObraDePrueba, obra_minima, otra_escena, transicionar

# La tabla del diagrama de `docs/domain-knowledge.md`, escrita a mano aqui: si
# se leyera de la misma constante que implementa el codigo, la prueba solo
# diria que la constante es igual a si misma.
DIAGRAMA = {
    ("planificada", "en_borrador"),
    ("en_borrador", "en_revision"),
    ("en_revision", "en_borrador"),
    ("en_revision", "planificada"),
    ("en_revision", "aceptada"),
    ("aceptada", "obsoleta"),
    ("obsoleta", "planificada"),
}

CAMINO_HASTA = {
    EstadoDeEscena.PLANIFICADA: (),
    EstadoDeEscena.EN_BORRADOR: (EstadoDeEscena.EN_BORRADOR,),
    EstadoDeEscena.EN_REVISION: (EstadoDeEscena.EN_BORRADOR, EstadoDeEscena.EN_REVISION),
    EstadoDeEscena.ACEPTADA: (
        EstadoDeEscena.EN_BORRADOR,
        EstadoDeEscena.EN_REVISION,
        EstadoDeEscena.ACEPTADA,
    ),
    EstadoDeEscena.OBSOLETA: (
        EstadoDeEscena.EN_BORRADOR,
        EstadoDeEscena.EN_REVISION,
        EstadoDeEscena.ACEPTADA,
        EstadoDeEscena.OBSOLETA,
    ),
}


def test_la_extraccion_no_es_un_estado_de_la_escena() -> None:
    assert {estado.value for estado in EstadoDeEscena} == {
        "planificada",
        "en_borrador",
        "en_revision",
        "aceptada",
        "obsoleta",
    }


def test_una_escena_nace_planificada(base: Conexion) -> None:
    obra = obra_minima(base)
    assert service.obtener_escena(base, obra.escena_id).estado is EstadoDeEscena.PLANIFICADA


def test_la_tabla_de_transiciones_es_la_del_diagrama() -> None:
    declaradas = {
        (origen.value, destino.value)
        for origen, destinos in TRANSICIONES.items()
        for destino in destinos
    }
    assert declaradas == DIAGRAMA


def test_la_escena_no_admite_transiciones_fuera_del_diagrama(base: Conexion) -> None:
    obra = obra_minima(base)
    for origen, destino in itertools.product(EstadoDeEscena, repeat=2):
        escena_id = _escena_en(base, obra, origen)
        par = (origen.value, destino.value)

        if par in DIAGRAMA:
            transicionar(base, escena_id, destino)
            assert service.obtener_escena(base, escena_id).estado is destino
        else:
            with pytest.raises(errores.TransicionInvalida):
                transicionar(base, escena_id, destino)
            assert service.obtener_escena(base, escena_id).estado is origen


def _escena_en(base: Conexion, obra: ObraDePrueba, estado: EstadoDeEscena) -> int:
    escena_id = otra_escena(base, obra)
    for paso in CAMINO_HASTA[estado]:
        transicionar(base, escena_id, paso)
    return escena_id
