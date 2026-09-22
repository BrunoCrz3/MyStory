"""H3 · pruebas 7, 8, 10 y 12 — RF-CANON-03, RF-CANON-04, RF-CANON-12, RF-CANON-15.

El snapshot es derivado. No hay una columna con «el estado del mundo» dentro: si
la hubiera, habria dos fuentes de verdad y la que se consulta no seria la que
los hechos dicen.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from app.canon import service
from app.canon.models import EstatusDeHecho, TipoDeHecho
from app.commons.db.conexion import Conexion
from tests.canon import fabrica

SIN_PLAZO = settings(max_examples=20, deadline=None)


def test_el_snapshot_es_derivado_y_nunca_texto_bruto(base: Conexion) -> None:
    """RF-CANON-03."""
    mundo = fabrica.mundo(base)
    escena = mundo.escena_consolidada(
        hechos=[
            mundo.hecho(TipoDeHecho.ESTADO_VITAL, sujeto=mundo.ilia, valor="vivo"),
            mundo.hecho(TipoDeHecho.UBICACION, sujeto=mundo.ilia, lugar=mundo.vado),
            mundo.hecho(TipoDeHecho.POSESION, sujeto=mundo.ilia, artefacto=mundo.llave),
        ],
        fecha_ficcional="ano 12 del vado",
    )

    snapshot = service.snapshot_en(base, escena)

    assert snapshot.personajes_vivos == [mundo.ilia]
    assert snapshot.ubicaciones == {mundo.ilia: mundo.vado}
    assert snapshot.posesiones == {mundo.llave: mundo.ilia}
    assert snapshot.fecha_ficcional == "ano 12 del vado"

    # Lo derivado no se guarda: la fila de `snapshot_mundo` no lleva el estado.
    columnas = {fila["name"] for fila in base.execute("PRAGMA table_info(snapshot_mundo)")}
    assert not columnas & {"personajes_vivos", "ubicaciones", "posesiones", "relaciones"}
    assert columnas >= {"escena_id", "version", "fecha_ficcional"}

    # Y se deriva de los hechos: si el hecho deja de estar vigente, el snapshot cambia.
    siguiente = mundo.escena_consolidada(
        hechos=[mundo.hecho(TipoDeHecho.UBICACION, sujeto=mundo.ilia, lugar=mundo.orilla)]
    )
    assert service.snapshot_en(base, siguiente).ubicaciones == {mundo.ilia: mundo.orilla}
    assert service.snapshot_en(base, escena).ubicaciones == {mundo.ilia: mundo.vado}


def test_el_estado_epistemico_registra_agente_hecho_y_escena_en_que_lo_aprende(
    base: Conexion,
) -> None:
    """RF-CANON-04. Y responde la pregunta de competencia 1."""
    mundo = fabrica.mundo(base)
    primera = mundo.escena_consolidada(
        hechos=[mundo.hecho(TipoDeHecho.DESCRIPTIVO, sujeto=mundo.ilia, valor="el rio habla")]
    )
    hecho_id = service.hechos_establecidos_en(base, primera)[0].id

    segunda = mundo.escena_consolidada(
        hechos=[],
        epistemicos=[fabrica.aprende(mundo.baro, hecho_id, certeza="sospecha")],
    )

    sabido = service.que_sabe(base, mundo.baro, hasta_escena_id=segunda)
    assert [(e.hecho_id, e.escena_id, e.certeza) for e in sabido] == [
        (hecho_id, segunda, "sospecha")
    ]
    assert service.que_sabe(base, mundo.baro, hasta_escena_id=primera) == []
    assert service.que_sabe(base, mundo.ilia, hasta_escena_id=segunda) == []


@SIN_PLAZO
@given(cuantas=st.integers(min_value=2, max_value=5))
def test_todo_cambio_entre_snapshots_tiene_un_hecho_detras(cuantas: int) -> None:
    """P-39, RF-CANON-12. Incluye posesiones y relaciones.

    El punto ciego declarado se asume: exige causa registrada, no causa creible.
    Un hecho establecido en la misma escena justifica cualquier salto.
    """
    with fabrica.base_nueva() as base:
        mundo = fabrica.mundo(base, escenas=cuantas + 1)
        escenas = [
            mundo.escena_consolidada(hechos=mundo.hechos_que_mueven_el_mundo(paso))
            for paso in range(cuantas)
        ]

        for anterior, siguiente in zip(escenas, escenas[1:], strict=False):
            antes = service.snapshot_en(base, anterior)
            despues = service.snapshot_en(base, siguiente)
            cambios = service.diferencias_entre_snapshots(antes, despues)
            respaldo = {
                (hecho.tipo, hecho.sujeto_personaje_id, hecho.artefacto_id)
                for hecho in service.hechos_establecidos_en(base, siguiente)
            }
            for cambio in cambios:
                assert (cambio.tipo, cambio.sujeto_personaje_id, cambio.artefacto_id) in respaldo, (
                    f"el cambio {cambio} no tiene hecho detras en la escena {siguiente}"
                )


@SIN_PLAZO
@given(distancia=st.integers(min_value=1, max_value=3))
def test_un_hecho_con_alcance_abierto_sigue_vigente_hasta_que_otro_lo_cierre(
    distancia: int,
) -> None:
    """P-48, RF-CANON-15.

    El punto ciego declarado se asume: necesita el alcance relleno. Un hecho sin
    alcance no caduca nunca ni contradice a nadie, y una herida desaparece sin
    violar nada.
    """
    with fabrica.base_nueva() as base:
        mundo = fabrica.mundo(base, escenas=distancia + 2)
        apertura = mundo.escena_consolidada(
            hechos=[mundo.hecho(TipoDeHecho.UBICACION, sujeto=mundo.ilia, lugar=mundo.vado)]
        )
        abierto = service.hechos_establecidos_en(base, apertura)[0]
        assert abierto.vigente_hasta_escena_id is None, "nace con el alcance abierto"

        intermedias = [mundo.escena_consolidada(hechos=[]) for _ in range(distancia)]
        cierre = mundo.escena_consolidada(
            hechos=[mundo.hecho(TipoDeHecho.UBICACION, sujeto=mundo.ilia, lugar=mundo.orilla)]
        )

        for escena in [apertura, *intermedias]:
            vigentes = {h.id for h in service.hechos_vigentes_en(base, escena)}
            assert abierto.id in vigentes

        vigentes_al_cierre = {h.id for h in service.hechos_vigentes_en(base, cierre)}
        assert abierto.id not in vigentes_al_cierre

        # Cerrar deja constancia de quien cierra: sin eso no se puede auditar.
        cerrado = service.obtener_hecho(base, abierto.id)
        assert cerrado.vigente_hasta_escena_id == cierre
        assert cerrado.estatus is EstatusDeHecho.CONFIRMADO
