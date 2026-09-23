"""H5 · pruebas 4, 6, 7 y 10 — RF-QUA-02 a RF-QUA-05, P-29.

Una dimension sin umbral es una opinion, no una metrica. v1 entrega las catorce
`T` puntuadas y **ninguna calibrada**: por eso mide, registra y no suspende.
"""

from __future__ import annotations

from app.commons.db.conexion import Conexion
from app.quality import service as calidad
from app.quality.models import AlcanceDelDefecto
from tests.quality import fabrica


def test_se_puntuan_las_catorce_dimensiones_clasificadas_t(base: Conexion) -> None:
    """RF-QUA-02. Las que lista `config/thresholds.yaml` bajo `calidad`, ni una mas.

    Las `D` y las `U` quedan fuera de v1: caracterizacion, curva de tension y
    sentido de la maravilla no tienen criterio de aprobado medible.
    """
    mundo = fabrica.mundo_criticable(base)
    umbrales = fabrica.umbrales()
    declaradas = set(umbrales.calidad.model_dump())
    assert len(declaradas) == 14

    informe = calidad.criticar(base, umbrales, fabrica.peticion(mundo))

    assert {puntuacion.dimension for puntuacion in informe.puntuaciones} == declaradas


def test_las_dimensiones_que_v1_no_puede_medir_se_declaran_y_no_inventan_valor(
    base: Conexion,
) -> None:
    """Tres de las catorce no se puntuan, y cada una dice por que.

    Devolver un numero seria peor que no devolverlo: una cifra inventada con
    aspecto de medida entra en el historial y contamina la comparacion entre
    versiones de A-50.

    `distintividad_de_voz` es la unica de las tres que se cierra sola: en cuanto
    haya dialogo aceptado, el clasificador ciego la puntua.
    """
    mundo = fabrica.mundo_criticable(base)
    informe = calidad.criticar(base, fabrica.umbrales(), fabrica.peticion(mundo))

    sin_medir = {p.dimension for p in informe.puntuaciones if p.valor is None}
    assert sin_medir == {"originalidad", "consistencia_temporal", "distintividad_de_voz"}
    for dimension in sin_medir:
        assert fabrica.puntuacion(informe, dimension).motivo, dimension

    assert "linea base" in fabrica.puntuacion(informe, "originalidad").motivo


def test_la_distintividad_se_puntua_en_cuanto_hay_dialogo_aceptado(
    base: Conexion,
) -> None:
    mundo = fabrica.mundo_criticable(base)
    mundo.sembrar_dialogo_distinguible()

    informe = calidad.criticar(base, fabrica.umbrales(), fabrica.peticion(mundo))

    assert fabrica.puntuacion(informe, "distintividad_de_voz").valor is not None


def test_el_informe_liga_cada_defecto_a_la_dimension_que_viola(base: Conexion) -> None:
    """RF-QUA-03."""
    mundo = fabrica.mundo_criticable(base)
    mundo.declarar_voz_narrativa(persona="tercera", tiempo_verbal="pasado")

    informe = calidad.criticar(
        base,
        fabrica.umbrales(),
        fabrica.peticion(mundo, texto="Cruce el vado. Yo sabia el precio y no dije nada."),
    )

    assert informe.defectos
    declaradas = set(fabrica.umbrales().calidad.model_dump())
    for defecto in informe.defectos:
        assert defecto.dimension in declaradas
        assert defecto.descripcion


def test_un_defecto_se_clasifica_como_local_o_sistemico(base: Conexion) -> None:
    """P-29, RF-QUA-04.

    La regla es la columna «Nivel» de la Capa 4: lo que se mide en la escena o
    en la frase se corrige reescribiendo en sitio; lo que se mide en la obra, en
    la parte o en el capitulo invalida la planificacion.

    El punto ciego declarado se asume y es severo: el dataset lo etiqueta quien
    construyo el clasificador, asi que mide acuerdo consigo mismo. Por eso la
    regla se deriva de la ontologia y no de un criterio propio.
    """
    mundo = fabrica.mundo_criticable(base)
    mundo.declarar_voz_narrativa(persona="tercera", tiempo_verbal="pasado")

    informe = calidad.criticar(
        base,
        fabrica.umbrales(),
        fabrica.peticion(mundo, texto="Cruce el vado. Yo sabia el precio y no dije nada."),
    )

    assert {defecto.alcance for defecto in informe.defectos} <= set(AlcanceDelDefecto)
    de_escena = [d for d in informe.defectos if d.dimension == "integridad_de_pov"]
    assert de_escena
    assert all(d.alcance is AlcanceDelDefecto.LOCAL for d in de_escena)

    assert calidad.nivel_de("ritmo") == "Parte"
    assert calidad.alcance_de("ritmo") is AlcanceDelDefecto.SISTEMICO
    assert calidad.alcance_de("integridad_de_pov") is AlcanceDelDefecto.LOCAL


def test_en_fase_de_medicion_ninguna_puntuacion_suspende(base: Conexion) -> None:
    """Criterio 4 de aceptacion, y punto ciego #15.

    Con `medicion.cerrar_el_paso` en `false` el critico puntua y registra, pero
    no suspende: quien acepta una escena es el autor, no el umbral. La fase es
    **consultable**, no un silencio, y va junto a cada puntuacion con el numero
    de escenas aceptadas desde que se declaro. Un corpus que ya da para calibrar
    y una fase que sigue abierta es una senal, no un estado.
    """
    mundo = fabrica.mundo_criticable(base)
    umbrales = fabrica.umbrales()
    assert umbrales.medicion.cerrar_el_paso is False

    informe = calidad.criticar(base, umbrales, fabrica.peticion(mundo))

    assert informe.fase_de_medicion is True
    assert informe.escenas_aceptadas >= 1
    assert all(puntuacion.suspende is False for puntuacion in informe.puntuaciones)
    assert all(puntuacion.umbral is None for puntuacion in informe.puntuaciones)


def test_con_umbrales_y_la_fase_cerrada_una_puntuacion_baja_suspende(
    base: Conexion,
) -> None:
    """RF-QUA-05. El mismo codigo decide cuando hay con que decidir."""
    mundo = fabrica.mundo_criticable(base)
    umbrales = fabrica.con_fase_cerrada(fabrica.umbrales(), umbral=0.99)

    informe = calidad.criticar(base, umbrales, fabrica.peticion(mundo))

    assert informe.fase_de_medicion is False
    medidas = [p for p in informe.puntuaciones if p.valor is not None]
    assert any(puntuacion.suspende for puntuacion in medidas)
    assert all(puntuacion.umbral == 0.99 for puntuacion in medidas)


def test_el_informe_se_guarda_y_se_consulta(base: Conexion) -> None:
    """RF-QUA-03: el informe es una entidad, no un valor de retorno."""
    mundo = fabrica.mundo_criticable(base)
    informe = calidad.criticar(base, fabrica.umbrales(), fabrica.peticion(mundo))

    guardados = calidad.informes_de(base, mundo.escena_id)
    assert [guardado.id for guardado in guardados] == [informe.id]
    assert guardados[0].version == informe.version
