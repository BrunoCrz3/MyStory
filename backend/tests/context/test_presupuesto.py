"""H4 · pruebas 1 a 6 — A-01, A-03, A-04, A-05, A-06, A-07.

La primera va primero porque es el limite duro de `AGENTS.md`: ningun prompt
puede superar `contexto.total`. Las demas describen que pasa cuando no cabe, y
todas dependen de que esa se cumpla.

El punto ciego de A-01 se asume y esta declarado: la propiedad se comprueba
contra el contador propio. Si el estimador cuenta menos que el tokenizador del
proveedor, el prompt cabe en la prueba y no en la ventana; lo que lo absorbe es
`contexto.capas.margen`, y quien lo confirma es A-09, ya despues de la llamada.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.commons import errores
from app.context import schemas
from app.context import service as contexto
from app.context.models import Capa
from tests.context import fabrica

SIN_PLAZO = settings(max_examples=15, deadline=None)


def test_las_siete_capas_mas_el_margen_suman_el_total() -> None:
    """A-07, RF-CTX-02. Ninguna cifra en el codigo: todas salen del fichero."""
    umbrales = fabrica.umbrales()
    capas = umbrales.contexto.capas.model_dump()

    assert set(capas) == {capa.value for capa in Capa}
    assert sum(capas.values()) == umbrales.contexto.total


def test_el_contexto_tiene_exactamente_siete_capas_mas_el_margen() -> None:
    """A-08, RF-CTX-01. Las del diagrama «Ensamblado del contexto»."""
    assert [capa.value for capa in Capa] == [
        "invariante",
        "estructural",
        "estado",
        "local",
        "recuperado",
        "estilo",
        "anticontexto",
        "margen",
    ]
    assert len(contexto.CAPAS_DEL_PROMPT) == 7
    assert Capa.MARGEN not in contexto.CAPAS_DEL_PROMPT
    assert set(contexto.FUENTE_DE_LA_CAPA) == set(contexto.CAPAS_DEL_PROMPT)


@SIN_PLAZO
@given(
    holgura=st.integers(min_value=0, max_value=40),
    fragmentos=st.integers(min_value=1, max_value=6),
)
def test_ningun_ensamblado_supera_contexto_total(holgura: int, fragmentos: int) -> None:
    """A-01, RNF-01. El limite duro."""
    with fabrica.base_nueva() as base:
        umbrales = fabrica.umbrales()
        dimension = umbrales.embeddings.dimension
        assert dimension is not None
        creado, escenas = fabrica.obra_indexada(base, dimension)

        for indice in range(fragmentos):
            fabrica.indexar(
                base,
                escenas[indice % len(escenas)],
                "Texto recuperable sobre el vado y la llave. " * (10 + holgura),
                [schemas.Referencia(tipo="personaje", id=creado.ilia)],
                semilla=0.5 + indice / 100,
                dimension=dimension,
            )

        ensamblado = contexto.ensamblar(
            base, umbrales, fabrica.peticion(creado, escenas[-1], dimension)
        )
        assert ensamblado.total <= umbrales.contexto.total
        assert sum(ensamblado.tokens_por_capa.values()) == ensamblado.total


def test_un_ensamblado_que_no_cabe_lanza_error_y_no_trunca(base_indexada) -> None:
    """A-03, RF-CTX-04. Truncar en silencio es el peor fallo del sistema.

    Lo que no se puede degradar es lo que puede desbordar: si la capa Invariante
    y la restriccion de destino ya no caben, no hay nada que comprimir y el
    ensamblado falla en voz alta.
    """
    base, creado, escenas, umbrales, dimension = base_indexada

    enorme = "premisa desmesurada " * 20000
    with pytest.raises(errores.PresupuestoExcedido) as detalle:
        contexto.ensamblar(
            base,
            umbrales,
            fabrica.peticion(creado, escenas[-1], dimension, guia_de_estilo=enorme),
        )
    assert "invariante" in str(detalle.value).lower()


def test_si_una_capa_desborda_se_comprime_esa_capa_sin_robar_a_otra(base_indexada) -> None:
    """A-04, RF-CTX-05.

    El punto ciego declarado se asume: no mide si lo que queda de la capa
    comprimida sigue sirviendo. Un snapshot podado hasta quedar vacio cumple.
    """
    base, creado, escenas, umbrales, dimension = base_indexada
    capas = umbrales.contexto.capas.model_dump()

    for indice in range(12):
        fabrica.indexar(
            base,
            escenas[indice % len(escenas)],
            "Fragmento recuperable larguisimo sobre el vado. " * 400,
            [],
            semilla=0.5 + indice / 100,
            dimension=dimension,
        )

    ensamblado = contexto.ensamblar(
        base, umbrales, fabrica.peticion(creado, escenas[-1], dimension)
    )

    for capa in contexto.CAPAS_DEL_PROMPT:
        assert ensamblado.tokens_por_capa[capa] <= capas[capa.value], capa
    assert ensamblado.total <= umbrales.contexto.total


def test_la_degradacion_sigue_el_orden_recuperado_estilo_local_estado_y_para_en_cuanto_cabe(
    base_indexada,
) -> None:
    """A-05, RF-CTX-06.

    El orden va de lo mas sustituible a lo menos: Recuperado pierde contexto
    lejano, Estilo fidelidad de voz, Local continuidad de prosa y Estado estado
    periferico.

    El punto ciego declarado se asume: comprueba el orden, no el punto de
    parada. Con un contador equivocado se degrada de mas y el orden sigue siendo
    correcto.
    """
    base, creado, escenas, umbrales, dimension = base_indexada

    assert umbrales.contexto.degradacion == ["recuperado", "estilo", "local", "estado"]

    # Un total ridiculo obliga a recorrer la escalera entera.
    apretado = _con_total(umbrales, 1200)
    ensamblado = contexto.ensamblar(
        base, apretado, fabrica.peticion(creado, escenas[-1], dimension)
    )

    assert [capa.value for capa in ensamblado.degradadas] == [
        valor
        for valor in apretado.contexto.degradacion
        if valor in {capa.value for capa in ensamblado.degradadas}
    ], "se degrada en el orden declarado"
    assert ensamblado.total <= apretado.contexto.total

    # Y para en cuanto cabe: con holgura no se degrada nada.
    holgado = contexto.ensamblar(base, umbrales, fabrica.peticion(creado, escenas[-1], dimension))
    assert holgado.degradadas == []


def test_la_capa_invariante_y_la_restriccion_de_destino_nunca_se_degradan(
    base_indexada,
) -> None:
    """A-06. Son lo que impide que la escena deje de ser de esta novela o deje
    de ir adonde tiene que ir."""
    base, creado, escenas, umbrales, dimension = base_indexada

    peticion = fabrica.peticion(creado, escenas[-1], dimension)
    apretado = _con_total(umbrales, 1200)
    ensamblado = contexto.ensamblar(base, apretado, peticion)

    assert Capa.INVARIANTE not in ensamblado.degradadas
    assert Capa.ESTRUCTURAL not in ensamblado.degradadas
    assert peticion.restriccion_de_destino in ensamblado.prompt

    invariante = [pieza for pieza in ensamblado.piezas if pieza.capa is Capa.INVARIANTE]
    sin_apretar = contexto.ensamblar(base, umbrales, peticion)
    assert invariante == [pieza for pieza in sin_apretar.piezas if pieza.capa is Capa.INVARIANTE]


def _con_total(umbrales, total: int):
    """Mismo reparto proporcional, otro total. Las cifras siguen saliendo del
    fichero: lo unico que cambia es la ventana que se simula."""
    capas = umbrales.contexto.capas.model_dump()
    original = umbrales.contexto.total
    escaladas = {nombre: max(valor * total // original, 1) for nombre, valor in capas.items()}
    escaladas["margen"] += total - sum(escaladas.values())
    return umbrales.model_copy(
        update={
            "contexto": umbrales.contexto.model_copy(
                update={
                    "total": total,
                    "capas": umbrales.contexto.capas.model_copy(update=escaladas),
                }
            )
        }
    )
