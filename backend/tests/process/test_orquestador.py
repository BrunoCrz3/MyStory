"""H6 · pruebas 2 y 6 — P-32, P-33, RF-PROC-05, RF-PROC-06.

Dos afirmaciones distintas y las dos son de la maquina, no del camino:

- **El siguiente paso sale del estado de la escena**, y de nada mas. Se recorre
  la tabla entera de `architecture.md` seccion Maquina de estados, las siete
  filas, no una muestra: lo que importa es tambien lo que **no** sale, y
  ninguna fila lleva a `aceptada`.
- **Al agotar las iteraciones la escena se queda en revision y escala.** Sin ese
  tope una escena que no converge gira entre `critico` y `editor` gastando
  presupuesto.

La tabla se escribe a mano aqui. Si se leyera de la misma constante que
implementa el codigo, la prueba solo diria que la constante es igual a si misma.
"""

from __future__ import annotations

import itertools

from app.novel.models import EstadoDeEscena
from app.process.orquestador import Paso, siguiente_paso
from app.quality.models import AlcanceDelDefecto

# `architecture.md`, seccion Maquina de estados. Clave: (estado, alcance del
# peor defecto sobre umbral). Valor: el agente que corre despues.
TABLA = {
    ("planificada", None): "redactor",
    ("en_borrador", None): "critico",
    ("en_revision", None): "verificador",
    ("en_revision", "local"): "editor",
    ("en_revision", "sistemico"): "replanificar",
    ("aceptada", None): "extractor",
    ("obsoleta", None): "replanificar",
}


def test_el_orquestador_elige_el_siguiente_paso_leyendo_el_estado_de_la_escena() -> None:
    for (estado, alcance), esperado in TABLA.items():
        paso = siguiente_paso(
            EstadoDeEscena(estado),
            alcance_del_peor_defecto=None if alcance is None else AlcanceDelDefecto(alcance),
            hay_informe=True,
        )
        assert paso.value == esperado, (estado, alcance)


def test_ninguna_fila_de_la_maquina_lleva_a_aceptada() -> None:
    """RF-PROC-07 visto desde la maquina: el orquestador nunca salta ese paso.

    Se recorre el producto cartesiano entero de estados y alcances, no las
    combinaciones que la tabla nombra: lo que se afirma es que **no existe**
    entrada que acepte, y para eso hay que mirar todas.
    """
    alcances: tuple[AlcanceDelDefecto | None, ...] = (None, *AlcanceDelDefecto)
    for estado, alcance, hay_informe in itertools.product(EstadoDeEscena, alcances, (False, True)):
        paso = siguiente_paso(estado, alcance_del_peor_defecto=alcance, hay_informe=hay_informe)
        assert paso is not Paso.EXTRACTOR or estado is EstadoDeEscena.ACEPTADA
        assert "acept" not in paso.value


def test_en_fase_de_medicion_ningun_defecto_desvia_la_escena() -> None:
    """Con `medicion.cerrar_el_paso` en false ninguna puntuacion suspende.

    No hay entonces defectos «sobre umbral», asi que la escena pasa siempre al
    verificador y las rutas de local y sistemico las abre el autor al leer el
    informe. La condicion de la tabla no cambia: lo que cambia es que su entrada
    llega vacia.
    """
    paso = siguiente_paso(
        EstadoDeEscena.EN_REVISION, alcance_del_peor_defecto=None, hay_informe=True
    )
    assert paso is Paso.VERIFICADOR


def test_en_revision_sin_informe_todavia_lo_que_falta_es_la_critica() -> None:
    paso = siguiente_paso(EstadoDeEscena.EN_REVISION, hay_informe=False)
    assert paso is Paso.CRITICO


def test_al_agotar_las_iteraciones_la_escena_se_queda_en_revision_y_escala() -> None:
    """P-33, RF-PROC-06. Escalar es un resultado valido, no un error."""
    for iteraciones in range(1, 5):
        paso = siguiente_paso(
            EstadoDeEscena.EN_REVISION,
            alcance_del_peor_defecto=AlcanceDelDefecto.LOCAL,
            hay_informe=True,
            iteraciones_de_revision=iteraciones,
            max_iteraciones_revision=3,
        )
        esperado = Paso.ESCALAR_AL_AUTOR if iteraciones >= 3 else Paso.EDITOR
        assert paso is esperado, iteraciones


def test_el_tope_solo_corta_en_revision() -> None:
    """Un corta-circuitos que parase una escena recien planificada no seria un
    corta-circuitos: seria un bloqueo."""
    for estado in (EstadoDeEscena.PLANIFICADA, EstadoDeEscena.EN_BORRADOR):
        paso = siguiente_paso(estado, iteraciones_de_revision=99, max_iteraciones_revision=1)
        assert paso is not Paso.ESCALAR_AL_AUTOR


def test_sin_tope_declarado_no_se_escala_por_iteraciones() -> None:
    """`orquestacion.max_iteraciones_revision` esta en null en v1.

    Un umbral que nadie ha puesto no decide. Es el mismo criterio que la fase de
    medicion, y esta escrito para que el dia que se ponga se vea que cambia.
    """
    paso = siguiente_paso(
        EstadoDeEscena.EN_REVISION,
        alcance_del_peor_defecto=AlcanceDelDefecto.LOCAL,
        hay_informe=True,
        iteraciones_de_revision=1000,
        max_iteraciones_revision=None,
    )
    assert paso is Paso.EDITOR
