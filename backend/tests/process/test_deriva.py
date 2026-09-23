"""H6 · pruebas 10, 11 y 12 — A-52, P-52, P-53, RF-PROC-08, RF-PROC-12, RF-PROC-13.

La definicion esta cerrada desde el 2026-09-22, asi que aqui ya se verifica la
**medida** y no solo el registro. Las cinco propiedades de la propuesta, en el
orden en que se escribieron, mas la densidad y el recalculo.

Dos cosas que conviene tener delante al leer estas pruebas:

- **La monotonia es cierta de `invalidacion` y falsa por diseno de los otros
  dos.** Pagar una promesa baja `inviabilidad_pago` y cerrar un hilo baja
  `canon_huerfano`: son justo los movimientos que la obra debe hacer para
  recoger su propio canon. Probar monotonia en los tres convertiria un acierto
  del sistema en un fallo.
- **El fixture de mutacion toca un componente y deja los otros dos quietos.** Esa
  es la mitad de su valor: una medida que se mueve entera ante cualquier cambio
  no distingue nada.
"""

from __future__ import annotations

import pytest

from app.commons import errores
from app.commons.db.conexion import Conexion
from app.process import service as proceso
from app.process.models import ComponenteDeDeriva, CuentaEn, MotivoDeIngrediente
from tests.process import fabrica

INVALIDACION = ComponenteDeDeriva.INVALIDACION
HUERFANO = ComponenteDeDeriva.CANON_HUERFANO
INVIABILIDAD = ComponenteDeDeriva.INVIABILIDAD_PAGO


def _valores(vector: object) -> dict[ComponenteDeDeriva, float]:
    return {
        componente: pieza.valor
        for componente, pieza in vector.componentes.items()  # type: ignore[attr-defined]
    }


def _medir(base: Conexion, escena_id: int, umbrales: object | None = None) -> object:
    return proceso.medir_deriva(base, umbrales or fabrica.umbrales(), escena_id)  # type: ignore[arg-type]


# --- Propiedad 1: cero tras un hito de plan --------------------------------


def test_la_deriva_vale_cero_tras_un_hito_de_plan(base: Conexion) -> None:
    """El plan que el autor acaba de escribir describe la obra por construccion.

    No es una tautologia del codigo: si el autor fija un plan que ya contradice
    el canon, la medida lo dice el primer dia. Lo que esta prueba afirma es que
    un plan coherente arranca en cero, y que ese cero es alcanzable.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    escena = mundo.escena_consolidada()
    mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla), fabrica.revelacion()])
    mundo.fijar_hito()

    vector = _medir(base, escena)

    assert _valores(vector) == {INVALIDACION: 0.0, HUERFANO: 0.0, INVIABILIDAD: 0.0}


# --- Propiedad 2: el *como* no cuenta --------------------------------------


def test_una_escena_que_cumple_su_restriccion_sin_hechos_nuevos_no_mueve_la_deriva(
    base: Conexion,
) -> None:
    """P-01. La escena descubre *como*, no *hacia donde*.

    Una escena que sale adelante sin establecer nada que el plan no supiera deja
    el vector igual. Es la prueba de que la medida no castiga escribir.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    primera = mundo.escena_consolidada()
    mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla)])
    mundo.fijar_hito()
    antes = _valores(_medir(base, primera))

    segunda = mundo.escena_consolidada()
    despues = _valores(_medir(base, segunda))

    assert despues == antes


# --- Propiedad 3: sube ante invalidacion inyectada -------------------------


def test_matar_a_un_personaje_que_una_restriccion_futura_necesita_sube_invalidacion(
    base: Conexion,
) -> None:
    """El fixture de mutacion: toca un componente y deja los otros dos quietos."""
    mundo = fabrica.mundo_del_ciclo(base)
    primera = mundo.escena_consolidada()
    mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla)])
    mundo.fijar_hito()
    antes = _valores(_medir(base, primera))
    assert antes[INVALIDACION] == 0.0

    muerte = mundo.matar(mundo.ilia)
    despues = _valores(_medir(base, muerte))

    assert despues[INVALIDACION] == 1.0
    assert despues[HUERFANO] == antes[HUERFANO]
    assert despues[INVIABILIDAD] == antes[INVIABILIDAD]


def test_un_estado_final_que_pide_al_personaje_vivo_se_invalida_al_morir(
    base: Conexion,
) -> None:
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    mundo.encargar([fabrica.estado_final(mundo.ilia, "vivo")])
    mundo.fijar_hito()

    muerte = mundo.matar(mundo.ilia)
    vector = _medir(base, muerte)

    assert _valores(vector)[INVALIDACION] == 1.0


def test_una_restriccion_que_ya_contaba_con_la_muerte_no_se_invalida(
    base: Conexion,
) -> None:
    """El control que separa «el canon cambio» de «el plan dejo de valer».

    Un plan que preve la muerte del personaje sigue describiendo la obra cuando
    el personaje muere. Sin este control, la medida estaria contando cambios de
    canon y no deriva.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    mundo.encargar([fabrica.estado_final(mundo.ilia, "muerto")])
    mundo.fijar_hito()

    muerte = mundo.matar(mundo.ilia)

    assert _valores(_medir(base, muerte))[INVALIDACION] == 0.0


def test_refutar_el_hecho_que_una_revelacion_iba_a_revelar_la_invalida(
    base: Conexion,
) -> None:
    """Una revelacion sin hecho que revelar no es una escena por escribir."""
    from app.canon import service as canon
    from app.canon.models import EstatusDeHecho

    mundo = fabrica.mundo_del_ciclo(base)
    hecho_id = mundo.hecho_descriptivo("el puente hablo la primera noche")
    mundo.encargar([fabrica.revelacion(hecho_id=hecho_id)])
    mundo.fijar_hito()
    escena = mundo.escena_consolidada()
    assert _valores(_medir(base, escena))[INVALIDACION] == 0.0

    canon.transicionar_hecho(base, hecho_id, EstatusDeHecho.REFUTADO)
    ultima = mundo.escena_consolidada()

    assert _valores(_medir(base, ultima))[INVALIDACION] == 1.0


# --- Propiedad 4: determinismo ---------------------------------------------


def test_la_deriva_es_determinista_para_el_mismo_canon_y_el_mismo_plan_hash(
    base: Conexion,
) -> None:
    """Sin esto el historico no sirve para calibrar, que es para lo unico que v1
    lo registra."""
    mundo = fabrica.mundo_del_ciclo(base)
    escena = mundo.escena_consolidada()
    mundo.promesa_pendiente()
    hilo = mundo.hilo()
    mundo.avanzar_hilo(hilo, escena)
    mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla), fabrica.revelacion()])
    mundo.fijar_hito()

    primera = _medir(base, escena)
    segunda = _medir(base, escena)

    assert _valores(primera) == _valores(segunda)
    assert primera.plan_hash == segunda.plan_hash  # type: ignore[attr-defined]
    assert proceso.recalcular_deriva(base, escena) == proceso.recalcular_deriva(base, escena)


# --- Propiedad 5: solo invalidacion es monotona ----------------------------


def test_solo_invalidacion_es_monotona(base: Conexion) -> None:
    """Entre hitos de plan y sin retcon de por medio.

    Dos personajes que una restriccion futura necesita, muertos uno tras otro:
    `invalidacion` sube y no baja. Los controles negativos --que los otros dos
    **si** bajan-- van en las dos pruebas siguientes.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    primera = mundo.escena_consolidada()
    mundo.encargar(
        [
            fabrica.posicion(mundo.ilia, mundo.orilla),
            fabrica.posicion(mundo.baro, mundo.vado),
        ]
    )
    mundo.fijar_hito()

    serie = [_valores(_medir(base, primera))[INVALIDACION]]
    serie.append(_valores(_medir(base, mundo.matar(mundo.ilia)))[INVALIDACION])
    serie.append(_valores(_medir(base, mundo.matar(mundo.baro)))[INVALIDACION])

    assert serie == sorted(serie), f"invalidacion bajo sin replanificar: {serie}"
    assert serie == [0.0, 0.5, 1.0]


def test_canon_huerfano_baja_al_cerrar_un_hilo(base: Conexion) -> None:
    """Control negativo. Cerrar un hilo es la obra recogiendo su propio canon."""
    from app.novel import service as novel
    from app.novel.models import EstadoDeHilo

    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla)])
    mundo.fijar_hito()

    hilo = mundo.hilo()
    abre = mundo.escena_consolidada()
    mundo.avanzar_hilo(hilo, abre)
    con_hilo = _valores(_medir(base, abre))[HUERFANO]
    assert con_hilo == 1.0, "un hilo abierto despues del hito es canon que el plan no recoge"

    novel.transicionar_hilo(base, hilo, EstadoDeHilo.CERRADO)
    cerrada = mundo.escena_consolidada()

    assert _valores(_medir(base, cerrada))[HUERFANO] < con_hilo


def test_inviabilidad_pago_baja_al_pagar_una_promesa(base: Conexion) -> None:
    """Control negativo.

    Con una sola candidata de pago declarada y dos promesas pendientes, al menos
    una se queda sin pagar: es la cuenta por palomar, que es lo unico que se
    puede afirmar mientras `alcance` no diga que restriccion recoge que promesa.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    mundo.encargar([fabrica.revelacion()])
    mundo.fijar_hito()

    primera = mundo.promesa_pendiente("que el rio conteste")
    mundo.promesa_pendiente("que la llave abra algo")
    con_dos = mundo.escena_consolidada()
    antes = _valores(_medir(base, con_dos))
    assert antes[INVIABILIDAD] == 0.5

    mundo.pagar(primera)
    pagada = mundo.escena_consolidada()
    despues = _valores(_medir(base, pagada))

    assert despues[INVIABILIDAD] < antes[INVIABILIDAD]
    assert despues[INVALIDACION] == antes[INVALIDACION]


def test_una_promesa_sin_ninguna_revelacion_futura_es_inviable(base: Conexion) -> None:
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla)])
    mundo.fijar_hito()

    mundo.promesa_pendiente()
    escena = mundo.escena_consolidada()

    assert _valores(_medir(base, escena))[INVIABILIDAD] == 1.0


# --- Prueba 11: densidad de declaracion (P-53) ----------------------------


def test_una_medicion_con_densidad_bajo_umbral_se_reporta_no_fiable(base: Conexion) -> None:
    """No basta con que salga baja.

    Un esquema que no declara nada tiene deriva cero para siempre: la medida, a
    solas, premia no planificar. Por debajo de su densidad la medicion se
    reporta **no fiable**, que no es lo mismo que reportarla baja.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    escena = mundo.escena_consolidada()
    mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla)])
    mundo.escena_por_escribir()  # planificada y sin declarar nada: ahi esta el agujero
    mundo.fijar_hito()

    exigente = fabrica.con_densidad_minima(fabrica.umbrales(), 1.0)
    vector = _medir(base, escena, exigente)

    assert vector.densidad.numerador == 1  # type: ignore[attr-defined]
    assert vector.densidad.denominador == 2  # type: ignore[attr-defined]
    assert vector.fiable is False  # type: ignore[attr-defined]
    assert _valores(vector)[INVALIDACION] == 0.0, "y aun asi la deriva sale baja: ese es el punto"


def test_con_densidad_suficiente_la_medicion_se_reporta_fiable(base: Conexion) -> None:
    mundo = fabrica.mundo_del_ciclo(base)
    escena = mundo.escena_consolidada()
    mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla), fabrica.revelacion()])
    mundo.fijar_hito()

    vector = _medir(base, escena, fabrica.con_densidad_minima(fabrica.umbrales(), 1.0))

    assert vector.fiable is True  # type: ignore[attr-defined]


def test_sin_umbral_de_densidad_la_fiabilidad_no_se_inventa(base: Conexion) -> None:
    """`densidad_declaracion_minima` esta en null en v1.

    `None` no es «fiable»: es «nadie ha dicho todavia con que se compara».
    Devolver `True` ahi seria exactamente el numero inventado que la fase de
    medicion existe para no dar.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    escena = mundo.escena_consolidada()
    mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla)])
    mundo.fijar_hito()

    assert _medir(base, escena).fiable is None  # type: ignore[attr-defined]


# --- Prueba 12: los ingredientes bastan (A-52, RF-PROC-12) ----------------


def test_los_ingredientes_bastan_para_recalcular_el_vector_sin_regenerar_nada(
    base: Conexion,
) -> None:
    """A-52. El vector se recalcula desde `deriva_ingrediente` y da lo mismo.

    Las columnas se calcularon contra el canon; el recalculo solo mira los
    ingredientes. Que coincidan es lo que hace del historico algo aprovechable:
    el dia que la definicion cambie no habra que regenerar la obra.

    El punto ciego declarado se asume: garantiza que los ingredientes cuadran
    con el vector, no que sean los que una definicion futura necesite.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.encargar(
        [
            fabrica.posicion(mundo.ilia, mundo.orilla),
            fabrica.posicion(mundo.baro, mundo.vado),
            fabrica.revelacion(),
        ]
    )
    mundo.fijar_hito()
    mundo.promesa_pendiente("que el rio conteste")
    mundo.promesa_pendiente("que la llave abra algo")
    hilo = mundo.hilo()
    escena = mundo.matar(mundo.ilia)
    mundo.avanzar_hilo(hilo, escena)

    vector = _medir(base, escena)
    recalculado = proceso.recalcular_deriva(base, escena)

    for componente, pieza in vector.componentes.items():  # type: ignore[attr-defined]
        assert recalculado[componente].numerador == pieza.numerador, componente
        assert recalculado[componente].denominador == pieza.denominador, componente
        assert recalculado[componente].valor == pieza.valor, componente


def test_cada_ingrediente_dice_por_que_cuenta(base: Conexion) -> None:
    """El motivo es corto y enumerado, no prosa libre: recalcular con otra
    definicion tiene que ser un `SELECT`, no una lectura a mano."""
    from app.process import repository

    mundo = fabrica.mundo_del_ciclo(base)
    mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla)])
    mundo.fijar_hito()
    escena = mundo.matar(mundo.ilia)
    _medir(base, escena)

    ingredientes = repository.ingredientes_de(base, escena)
    numeradores = [
        ingrediente
        for ingrediente in ingredientes
        if ingrediente.componente is INVALIDACION and ingrediente.cuenta_en is CuentaEn.NUMERADOR
    ]
    assert [ingrediente.motivo for ingrediente in numeradores] == [
        MotivoDeIngrediente.POSICION_IMPOSIBLE
    ]
    assert all(isinstance(i.motivo, MotivoDeIngrediente) for i in ingredientes)


# --- El hito de plan como ancla (RF-PROC-13) ------------------------------


def test_medir_sin_hito_de_plan_falla_en_voz_alta(base: Conexion) -> None:
    mundo = fabrica.mundo_del_ciclo(base)
    escena = mundo.escena_consolidada()
    mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla)])

    with pytest.raises(errores.PlanCambiadoSinHito):
        _medir(base, escena)


def test_cambiar_el_plan_sin_registrar_el_motivo_impide_medir(base: Conexion) -> None:
    """RF-PROC-13. En v1 editar el esquema a mano es la unica forma de
    replanificar, y esas decisiones son las etiquetas con las que se calibran los
    umbrales. Un cambio sin motivo deja el dato sin la mitad que lo hace util.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    escena = mundo.escena_consolidada()
    mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla)])
    mundo.fijar_hito("plan inicial")
    _medir(base, escena)

    mundo.encargar([fabrica.revelacion()])
    with pytest.raises(errores.PlanCambiadoSinHito):
        _medir(base, escena)

    mundo.fijar_hito("la revelacion se mueve al capitulo siguiente")
    assert _medir(base, escena) is not None


def test_cada_hito_guarda_su_motivo_y_su_huella(base: Conexion) -> None:
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla)])
    mundo.fijar_hito("plan inicial")
    mundo.encargar([fabrica.revelacion()])
    mundo.fijar_hito("hace falta una revelacion antes del cierre")

    hitos = proceso.hitos(base)
    assert [hito.motivo for hito in hitos] == [
        "plan inicial",
        "hace falta una revelacion antes del cierre",
    ]
    assert hitos[0].plan_hash != hitos[1].plan_hash


def test_la_deriva_solo_se_mide_de_una_escena_aceptada(base: Conexion) -> None:
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    brief = mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla)])
    mundo.fijar_hito()

    with pytest.raises(errores.DerivaSoloDeEscenaAceptada):
        _medir(base, brief.escena_id)


def test_el_historico_sale_en_orden_de_discurso(base: Conexion) -> None:
    """Es una serie temporal: leerla desordenada no serviria para calibrar."""
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla)])
    mundo.fijar_hito()
    primera = mundo.escena_consolidada()
    segunda = mundo.escena_consolidada()
    _medir(base, segunda)
    _medir(base, primera)

    historico = proceso.historico(base, fabrica.umbrales())
    assert [medida.escena_id for medida in historico] == [primera, segunda]
