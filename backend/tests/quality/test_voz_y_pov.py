"""H5 · pruebas 3 y 5 — P-08, P-11, P-42, RF-QUA-09.

La persona y el tiempo verbal son deterministas: dejan marca morfologica. El
punto ciego declarado se asume — el cambio de distancia o de focalizacion dentro
del mismo tiempo verbal no la deja.
"""

from __future__ import annotations

from app.commons.db.conexion import Conexion
from app.quality import service as calidad
from app.quality import voz as muestreo
from tests.quality import fabrica


def test_el_borrador_respeta_la_persona_y_el_tiempo_verbal_de_voz_narrativa(
    base: Conexion,
) -> None:
    """P-42, RF-QUA-09, primera mitad."""
    mundo = fabrica.mundo_criticable(base)
    mundo.declarar_voz_narrativa(persona="tercera", tiempo_verbal="pasado")

    conforme = calidad.verificar_voz_narrativa(
        base, fabrica.peticion(mundo, texto="Ilia cruzó el vado y no miró atrás.")
    )
    assert conforme == []

    en_primera = calidad.verificar_voz_narrativa(
        base, fabrica.peticion(mundo, texto="Crucé el vado y no miré atrás. Yo sabía el precio.")
    )
    assert any("persona" in defecto.descripcion for defecto in en_primera)

    en_presente = calidad.verificar_voz_narrativa(
        base, fabrica.peticion(mundo, texto="Ilia cruza el vado y no mira atrás.")
    )
    assert any("tiempo" in defecto.descripcion for defecto in en_presente)


def test_una_escena_tiene_un_solo_pov(base: Conexion) -> None:
    """P-42, RF-QUA-09, segunda mitad, y P-11.

    El punto ciego declarado se asume: detecta el verbo de acceso ajeno («supo
    que ella temia»); no detecta la fuga por descripcion de lo que el POV no
    puede ver.
    """
    mundo = fabrica.mundo_criticable(base)
    mundo.declarar_voz_narrativa(persona="tercera", tiempo_verbal="pasado")

    fuga = calidad.verificar_voz_narrativa(
        base,
        fabrica.peticion(
            mundo,
            texto="Ilia cruzó el vado. Baro pensó que aquello terminaría mal y sintió frío.",
            pov_personaje_id=mundo.ilia,
        ),
    )
    assert any("pov" in defecto.descripcion.lower() for defecto in fuga)

    limpio = calidad.verificar_voz_narrativa(
        base,
        fabrica.peticion(
            mundo,
            texto="Ilia cruzó el vado. Pensó que aquello terminaría mal. Baro callaba.",
            pov_personaje_id=mundo.ilia,
        ),
    )
    assert limpio == []


def test_se_identifica_quien_habla_sin_acotaciones(base: Conexion) -> None:
    """P-08, RF-QUA-02, solucion picara #10.

    Clasificador ciego entrenado sobre el dialogo ya aceptado de la obra y
    evaluado **dejando fuera** al personaje que se juzga. Determinista, sin
    anotador y sin semilla que ajustar.

    **La letra de esta fila depende de la pregunta abierta #6.** Si el autor
    decide que quien clasifica es una persona, `P-08` pasa a `D` y sale de v1;
    esto es solo el candidato barato que `verification.md` propone, y por eso la
    prueba mide separacion frente al azar, no una puntuacion absoluta.
    """
    mundo = fabrica.mundo_criticable(base)
    mundo.sembrar_dialogo_distinguible()

    medida = muestreo.clasificacion_ciega(base, [mundo.ilia, mundo.baro], mundo.escena_id)

    assert medida.evaluados > 0
    assert medida.azar == 0.5
    assert medida.acierto > medida.azar, "las dos voces se distinguen sin acotaciones"


def test_sin_corpus_suficiente_la_distintividad_no_se_puntua(base: Conexion) -> None:
    """Un clasificador sin nada con lo que entrenar no acierta: no mide.

    Devolver 0.0 seria decir que las voces no se distinguen. Lo cierto es que
    todavia no se sabe, y eso es lo que se reporta.
    """
    mundo = fabrica.mundo_criticable(base)

    medida = muestreo.clasificacion_ciega(base, [mundo.ilia, mundo.baro], mundo.escena_id)

    assert medida.evaluados == 0
    assert medida.acierto is None


def test_una_escena_sin_personajes_declarados_no_intenta_clasificar(base: Conexion) -> None:
    """Regresion. Con la lista vacia --o con una sola voz-- no hay a quien
    confundir, y antes se entraba igual al recuento hasta dividir por cero.

    Decir 0.0 seria decir que las voces no se distinguen; lo cierto es que no
    hay dos voces que comparar, y eso es lo que se reporta.
    """
    mundo = fabrica.mundo_criticable(base)
    mundo.sembrar_dialogo_distinguible()

    for presentes in ([], [mundo.ilia]):
        medida = muestreo.clasificacion_ciega(base, presentes, mundo.escena_id)
        assert medida.evaluados == 0
        assert medida.acierto is None
