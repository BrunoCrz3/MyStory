"""H3 · pruebas 1, 2, 3 y 11 — A-16, A-27, A-28, A-48.

La primera va primero a proposito: es el invariante cuyo incumplimiento
contamina todo lo demas y no se nota hasta mucho despues. Si un borrador
rechazado deja rastro, cada iteracion fallida ensucia el estado del mundo y la
escena siguiente se genera contra un canon que nadie escribio.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.canon import schemas, service
from app.canon.models import EstatusDeHecho, TipoDeHecho
from app.commons import errores
from app.commons.db.conexion import Conexion
from app.novel import service as novel
from app.novel.models import EstadoDeEscena
from tests.canon import fabrica

SIN_PLAZO = settings(max_examples=25, deadline=None)

CAMINO_HASTA = {
    EstadoDeEscena.PLANIFICADA: (),
    EstadoDeEscena.EN_BORRADOR: (EstadoDeEscena.EN_BORRADOR,),
    EstadoDeEscena.EN_REVISION: (EstadoDeEscena.EN_BORRADOR, EstadoDeEscena.EN_REVISION),
    EstadoDeEscena.OBSOLETA: (
        EstadoDeEscena.EN_BORRADOR,
        EstadoDeEscena.EN_REVISION,
        EstadoDeEscena.ACEPTADA,
        EstadoDeEscena.OBSOLETA,
    ),
}


def _consolidacion(mundo: fabrica.Mundo, escena_id: int, version: int = 1) -> schemas.Consolidacion:
    hecho = mundo.hecho(TipoDeHecho.UBICACION, sujeto=mundo.ilia, lugar=mundo.vado)
    return schemas.Consolidacion(
        escena_id=escena_id,
        version=version,
        texto=f"{hecho.texto}. Ilia llego a El vado al anochecer.",
        fecha_ficcional="ano 12 del vado",
        hechos=[hecho],
    )


# --- 1. El invariante que lo contamina todo -------------------------------


@SIN_PLAZO
@given(
    estado=st.sampled_from(sorted(CAMINO_HASTA, key=lambda e: e.value)),
    cuantos_hechos=st.integers(min_value=1, max_value=4),
)
def test_un_borrador_rechazado_no_deja_rastro_en_el_canon(
    estado: EstadoDeEscena, cuantos_hechos: int
) -> None:
    """A-27, RF-CANON-07. Sea cual sea el estado, si no es `aceptada` no escribe."""
    with fabrica.base_nueva() as base:
        mundo = fabrica.mundo(base)
        escena_id = mundo.escena(0)
        for paso in CAMINO_HASTA[estado]:
            novel.transicionar_escena(base, escena_id, paso)

        antes = service.inventario_del_canon(base)
        assert antes == dict.fromkeys(antes, 0), "la base de partida no tenia canon"

        intento = _consolidacion(mundo, escena_id)
        intento = intento.model_copy(update={"hechos": intento.hechos * cuantos_hechos})

        with pytest.raises(errores.CanonSoloAlAceptar):
            service.consolidar_escena(base, intento)

        assert service.inventario_del_canon(base) == antes


def test_solo_la_transicion_a_aceptada_escribe_en_el_canon(base: Conexion) -> None:
    """A-28."""
    mundo = fabrica.mundo(base)
    escena_id = mundo.escena(0)

    assert service.inventario_del_canon(base)["hecho_canonico"] == 0
    fabrica.aceptar(base, escena_id)
    assert service.inventario_del_canon(base)["hecho_canonico"] == 0, (
        "aceptar no escribe por si solo: escribe consolidar la escena aceptada"
    )

    service.consolidar_escena(base, _consolidacion(mundo, escena_id))
    assert service.inventario_del_canon(base)["hecho_canonico"] == 1


# --- 3. Idempotencia ------------------------------------------------------


@SIN_PLAZO
@given(repeticiones=st.integers(min_value=2, max_value=5))
def test_consolidar_es_idempotente_por_scene_id_y_version(repeticiones: int) -> None:
    """A-16, RF-CANON-08. Reintentar no puede consolidar dos veces."""
    with fabrica.base_nueva() as base:
        mundo = fabrica.mundo(base)
        escena_id = mundo.escena(0)
        fabrica.aceptar(base, escena_id)

        primero = service.consolidar_escena(base, _consolidacion(mundo, escena_id))
        for _ in range(repeticiones - 1):
            repetido = service.consolidar_escena(base, _consolidacion(mundo, escena_id))
            assert repetido == primero

        assert service.inventario_del_canon(base)["hecho_canonico"] == 1


def test_una_version_posterior_de_la_misma_escena_sustituye_y_no_duplica(
    base: Conexion,
) -> None:
    """Cierra el punto ciego que `verification.md` anota en A-16.

    Dos consolidaciones de la misma escena con `version` distinta duplicarian
    hechos sin violar ninguna restriccion. Una escena reescrita sustituye lo que
    dejo la version anterior: si no, el canon acumula las dos y se contradicen.
    """
    mundo = fabrica.mundo(base)
    escena_id = mundo.escena(0)
    fabrica.aceptar(base, escena_id)

    service.consolidar_escena(base, _consolidacion(mundo, escena_id, version=1))
    service.consolidar_escena(base, _consolidacion(mundo, escena_id, version=2))

    assert service.inventario_del_canon(base)["hecho_canonico"] == 1
    assert service.version_consolidada(base, escena_id) == 2


def test_la_consolidacion_ocurre_dentro_de_una_transaccion(base: Conexion) -> None:
    """RF-CANON-08. Si un hecho no ancla, no entra ninguno."""
    mundo = fabrica.mundo(base)
    escena_id = mundo.escena(0)
    fabrica.aceptar(base, escena_id)

    bueno = mundo.hecho(TipoDeHecho.UBICACION, sujeto=mundo.ilia, lugar=mundo.vado)
    malo = schemas.NuevoHechoCanonico(
        texto="Mirel incendio la torre del reloj",
        tipo=TipoDeHecho.DESCRIPTIVO,
        estatus=EstatusDeHecho.CONFIRMADO,
    )
    with pytest.raises(errores.HechoSinAnclaje):
        service.consolidar_escena(
            base,
            schemas.Consolidacion(
                escena_id=escena_id,
                version=1,
                texto=f"{bueno.texto}. Ilia llego a El vado.",
                hechos=[bueno, malo],
            ),
        )

    inventario = service.inventario_del_canon(base)
    assert inventario == dict.fromkeys(inventario, 0)


# --- 11. Anclaje textual --------------------------------------------------


def test_los_terminos_de_un_hecho_aparecen_en_la_escena_que_lo_establece(
    base: Conexion,
) -> None:
    """A-48, RF-CANON-11. Es lo unico que ata el canon a la prosa de la que salio.

    El punto ciego declarado sigue abierto y se asume: comprueba presencia de
    terminos, no lo que el hecho afirma. Un hecho que invierte el sentido con
    las mismas palabras pasa.
    """
    mundo = fabrica.mundo(base)
    escena_id = mundo.escena(0)
    fabrica.aceptar(base, escena_id)

    huerfano = schemas.Consolidacion(
        escena_id=escena_id,
        version=1,
        texto="Ilia llego a El vado al anochecer.",
        hechos=[
            schemas.NuevoHechoCanonico(
                texto="Mirel incendio la torre del reloj",
                tipo=TipoDeHecho.DESCRIPTIVO,
                estatus=EstatusDeHecho.CONFIRMADO,
            )
        ],
    )
    with pytest.raises(errores.HechoSinAnclaje) as detalle:
        service.consolidar_escena(base, huerfano)
    assert "Mirel" in str(detalle.value)

    service.consolidar_escena(base, _consolidacion(mundo, escena_id))
    assert service.inventario_del_canon(base)["hecho_canonico"] == 1


def test_el_anclaje_mira_tambien_las_entidades_referidas(base: Conexion) -> None:
    mundo = fabrica.mundo(base)
    escena_id = mundo.escena(0)
    fabrica.aceptar(base, escena_id)

    # «Baro» no aparece en el texto de la escena, aunque el hecho lo nombre como sujeto.
    con_entidad_ausente = schemas.Consolidacion(
        escena_id=escena_id,
        version=1,
        texto="Ilia llego a El vado con La llave de piedra.",
        hechos=[
            schemas.NuevoHechoCanonico(
                texto="alguien dejo La llave de piedra",
                tipo=TipoDeHecho.POSESION,
                estatus=EstatusDeHecho.CONFIRMADO,
                sujeto_personaje_id=mundo.baro,
                artefacto_id=mundo.llave,
            )
        ],
    )
    with pytest.raises(errores.HechoSinAnclaje):
        service.consolidar_escena(base, con_entidad_ausente)
