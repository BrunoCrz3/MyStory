"""H5 · prueba 2 — RF-QUA-01, P-02, P-03, P-04, P-05, P-07, P-37, P-38, P-40, P-51.

Los cuatro ejes contra el canon en `t`, mas los cuatro casos que entraron con la
auditoria. La epistemica va **en los dos sentidos**: ni usar lo que no se sabe,
ni ignorar lo que si.

Todo esto se resuelve con una consulta contra estado que el canon ya guarda. Es
barato y no espera a ningun umbral, que es justo por lo que entra en v1.
"""

from __future__ import annotations

from app.canon.models import TipoDeHecho
from app.commons.db.conexion import Conexion
from app.quality import service as calidad
from app.quality.models import Eje
from tests.quality import fabrica


def _ejes(defectos: list[object]) -> set[str]:
    return {defecto.eje.value for defecto in defectos}


def test_la_continuidad_detecta_un_hecho_que_contradice_el_canon(base: Conexion) -> None:
    """P-02, eje factico.

    El punto ciego declarado se asume: la parte programatica solo alcanza a lo
    enunciado con terminos canonicos y nombres propios.
    """
    mundo = fabrica.mundo_criticable(base)
    mundo.establecer(TipoDeHecho.UBICACION, sujeto=mundo.ilia, lugar=mundo.vado)

    defectos = calidad.verificar_continuidad(
        base,
        fabrica.peticion(
            mundo, texto="Ilia nunca había estado en El vado. La orilla norte la esperaba."
        ),
    )
    assert Eje.FACTICA.value in _ejes(defectos)


def test_ningun_personaje_no_vivo_actua_en_el_borrador(base: Conexion) -> None:
    """P-37.

    El punto ciego declarado se asume: cruza nombres propios. Un personaje
    muerto al que la escena alude sin nombrarlo se le escapa.
    """
    mundo = fabrica.mundo_criticable(base)
    mundo.establecer(TipoDeHecho.ESTADO_VITAL, sujeto=mundo.baro, valor="muerto")

    defectos = calidad.verificar_continuidad(
        base, fabrica.peticion(mundo, texto="Baro cruzó el vado y abrió la puerta.")
    )
    assert Eje.FACTICA.value in _ejes(defectos)
    assert any("Baro" in defecto.descripcion for defecto in defectos)


def test_un_artefacto_no_cambia_de_poseedor_sin_escena_que_lo_establezca(
    base: Conexion,
) -> None:
    """P-38.

    El punto ciego declarado se asume: sigue las posesiones declaradas. Un
    objeto que la escena introduce y que nadie registro no se sigue.
    """
    mundo = fabrica.mundo_criticable(base)
    mundo.establecer(TipoDeHecho.POSESION, sujeto=mundo.ilia, artefacto=mundo.llave)

    defectos = calidad.verificar_continuidad(
        base,
        fabrica.peticion(
            mundo, texto="Baro sacó La llave de piedra del bolsillo y abrió la puerta."
        ),
    )
    assert Eje.FACTICA.value in _ejes(defectos)


def test_la_continuidad_espacial_usa_el_snapshot_de_posiciones(base: Conexion) -> None:
    """P-04.

    El punto ciego declarado se asume: sabe donde estaba el personaje, no cuanto
    tarda en llegar. Sin duraciones declaradas, un desplazamiento imposible es
    indistinguible de uno lento.
    """
    mundo = fabrica.mundo_criticable(base)
    mundo.establecer(TipoDeHecho.UBICACION, sujeto=mundo.ilia, lugar=mundo.vado)

    defectos = calidad.verificar_continuidad(
        base, fabrica.peticion(mundo, texto="Ilia seguía en La orilla norte, sin moverse.")
    )
    assert Eje.ESPACIAL.value in _ejes(defectos)


def test_la_epistemica_detecta_usar_lo_que_no_se_sabe(base: Conexion) -> None:
    """P-05, primer sentido."""
    mundo = fabrica.mundo_criticable(base)
    hecho = mundo.establecer(
        TipoDeHecho.DESCRIPTIVO, sujeto=mundo.ilia, valor="el río guarda voces"
    )

    defectos = calidad.verificar_continuidad(
        base,
        fabrica.peticion(
            mundo,
            texto="Baro sabía que el río guarda voces y no dijo nada.",
            pov_personaje_id=mundo.baro,
        ),
    )
    assert Eje.EPISTEMICA.value in _ejes(defectos)
    assert any(str(hecho) in defecto.descripcion for defecto in defectos)


def test_la_epistemica_detecta_ignorar_lo_que_si_se_sabe(base: Conexion) -> None:
    """P-51, segundo sentido. Es la mitad que casi nadie implementa.

    El punto ciego declarado se asume: detecta la pregunta explicita, no el
    personaje que actua como si no supiera.
    """
    mundo = fabrica.mundo_criticable(base)
    hecho = mundo.establecer(
        TipoDeHecho.DESCRIPTIVO, sujeto=mundo.ilia, valor="el río guarda voces"
    )
    mundo.aprende(mundo.baro, hecho)

    defectos = calidad.verificar_continuidad(
        base,
        fabrica.peticion(
            mundo,
            texto="Baro preguntó si el río guarda voces, como si fuera la primera vez.",
            pov_personaje_id=mundo.baro,
        ),
    )
    assert Eje.EPISTEMICA.value in _ejes(defectos)


def test_una_revelacion_por_debajo_de_su_escena_minima_no_pasa(base: Conexion) -> None:
    """P-40.

    El punto ciego declarado se asume: cubre las revelaciones registradas; la
    que el borrador filtra sin que nadie la haya registrado, no.
    """
    mundo = fabrica.mundo_criticable(base)
    hecho = mundo.establecer(
        TipoDeHecho.DESCRIPTIVO, sujeto=mundo.ilia, valor="el puente tiene memoria"
    )
    mundo.prohibir_revelacion_antes_de(hecho, mundo.escena_futura())

    defectos = calidad.verificar_continuidad(
        base, fabrica.peticion(mundo, texto="Ilia dijo en voz alta: el puente tiene memoria.")
    )
    assert Eje.EPISTEMICA.value in _ejes(defectos)


def test_la_plausibilidad_especulativa_se_mide_contra_las_reglas_declaradas(
    base: Conexion,
) -> None:
    """P-07.

    El punto ciego declarado se asume: comprueba las reglas declaradas. Una
    consecuencia en cascada del novum que nadie escribio no la ve nadie.
    """
    mundo = fabrica.mundo_criticable(base)
    mundo.declarar_regla("el río solo habla en crecida")

    defectos = calidad.verificar_continuidad(
        base,
        fabrica.peticion(
            mundo, texto="Con el cauce seco, el río habló igualmente y nombró a Ilia."
        ),
    )
    assert Eje.ESPECULATIVA.value in _ejes(defectos)


def test_la_continuidad_temporal_se_reporta_no_evaluable_y_dice_por_que(
    base: Conexion,
) -> None:
    """P-03, y es el eje que v1 no puede medir.

    `Evento.momento_en_la_fabula` es texto libre y no hay relacion `Lugar`-`Lugar`
    con coste de desplazamiento: sin orden declarado ni duraciones no hay
    cronologia que comprobar. Las dos carencias estan en `verification.md`
    § Filas pendientes de ontologia, y son del documento vivo, no del plan.

    Lo que **no** se hace es devolver un numero: una cifra inventada con aspecto
    de medida entra en el historial y contamina la calibracion de A-50.
    """
    mundo = fabrica.mundo_criticable(base)
    informe = calidad.criticar(base, fabrica.umbrales(), fabrica.peticion(mundo))

    temporal = fabrica.puntuacion(informe, "consistencia_temporal")
    assert temporal.valor is None
    assert temporal.motivo and "texto libre" in temporal.motivo

    defectos = calidad.verificar_continuidad(base, fabrica.peticion(mundo))
    assert Eje.TEMPORAL.value not in _ejes(defectos)


def test_un_borrador_coherente_no_produce_defectos_de_continuidad(base: Conexion) -> None:
    mundo = fabrica.mundo_criticable(base)
    mundo.establecer(TipoDeHecho.UBICACION, sujeto=mundo.ilia, lugar=mundo.vado)

    defectos = calidad.verificar_continuidad(
        base,
        fabrica.peticion(mundo, texto="Ilia seguía en El vado, contando las horas sin prisa."),
    )
    assert defectos == []
