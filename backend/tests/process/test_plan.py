"""H6 · prueba 13 y RF-PROC-01 — P-41, RF-PROC-11.

El brief es minimo y el plan declara el futuro; y una escena no se adelanta a
el. Las dos mitades del modo hibrido visto desde `process/`: la escena descubre
*como*, no *hacia donde*.

El punto ciego de P-41 se asume y esta escrito: solo se ve lo declarado --los
tres `tipo` de restriccion y sus columnas cotejables--. Adelantar algo que el
esquema no escribio no es detectable por nadie.
"""

from __future__ import annotations

import pytest

from app.commons import errores
from app.commons.db.conexion import Conexion
from app.process import schemas as process_schemas
from app.process import service as proceso
from app.process.models import TipoDeRestriccion
from tests.process import fabrica

# --- RF-PROC-01: el brief minimo y el plan materializado ------------------


def test_el_brief_es_minimo_y_no_planifica_beats(base: Conexion) -> None:
    """Estado de entrada mas restriccion de destino, y nada mas.

    `Beat` es descubrimiento libre y su fuente de verdad es el texto generado.
    Que el contrato no tenga donde meterlos es la forma de que nadie los meta.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    brief = mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla)])

    assert set(process_schemas.NuevoBrief.model_fields) == {
        "escena_id",
        "estado_de_entrada",
        "encargo",
        "restricciones",
    }
    assert brief.estado_de_entrada
    assert [r.tipo for r in brief.restricciones] == [TipoDeRestriccion.POSICION_DE_PERSONAJE]


def test_un_brief_sin_restriccion_de_destino_no_entra(base: Conexion) -> None:
    """Sin destino la escena descubriria tambien hacia donde va, y la deriva se
    quedaria sin denominador."""
    mundo = fabrica.mundo_del_ciclo(base)
    escena = mundo.escena_por_escribir()

    with pytest.raises(errores.BriefSinRestriccionDeDestino):
        mundo.brief(escena, [])


def test_el_esquema_materializa_las_restricciones_de_todas_las_planificadas(
    base: Conexion,
) -> None:
    """RF-PROC-01, segunda frase.

    Si solo se declarara el brief de la escena siguiente, el denominador de la
    deriva seria 1 y la medida no diria nada. La vista del esquema es donde se
    comprueba, y es la misma que reporta la densidad.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.escena_consolidada()
    mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla)])
    mundo.encargar([fabrica.revelacion()])
    mundo.encargar([fabrica.estado_final(mundo.baro, "muerto")])

    esquema = proceso.esquema_declarado(base)

    assert esquema.restricciones_futuras == 3
    assert esquema.escenas_planificadas == 3

    # Y una escena planificada que no declara nada cuenta igual en el
    # denominador: es lo que hace honesta a la densidad. Un plan que se calla
    # no tiene densidad alta por callarse.
    mundo.escena_por_escribir()
    assert proceso.esquema_declarado(base).escenas_planificadas == 4
    assert proceso.esquema_declarado(base).restricciones_futuras == 3


def test_el_esquema_dice_si_alguien_lo_movio_sin_registrarlo(base: Conexion) -> None:
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla)])
    mundo.fijar_hito("plan inicial")
    assert proceso.esquema_declarado(base).coincide_con_el_hito is True

    mundo.encargar([fabrica.revelacion()])
    assert proceso.esquema_declarado(base).coincide_con_el_hito is False


def test_la_huella_del_plan_no_depende_del_orden_de_insercion(base: Conexion) -> None:
    """Lo que identifica al plan es lo que declara, no como se tecleo.

    Sin esto, reescribir una restriccion identica inventaria un hito y el
    historico se llenaria de replanificaciones que nadie hizo.
    """
    from app.process import deriva, repository

    mundo = fabrica.mundo_del_ciclo(base)
    mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla)])
    mundo.encargar([fabrica.revelacion()])
    declaradas = repository.restricciones_de_escenas_planificadas(base)

    assert deriva.huella_del_plan(declaradas) == deriva.huella_del_plan(list(reversed(declaradas)))


# --- RF-PROC-11 / P-41: no adelantarse al plan ----------------------------


def test_un_borrador_no_satisface_el_destino_de_un_brief_posterior(base: Conexion) -> None:
    """El cotejo de la picara 5, corrido hacia adelante.

    Una escena que ya deja al personaje donde la N+k lo queria se ha adelantado
    al plan. En v1 el resultado es informacion para el autor: con `replanning/`
    fuera, replanifica una persona.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.encargar([fabrica.posicion(mundo.ilia, mundo.orilla)])

    limpia = mundo.situar(mundo.ilia, mundo.vado)
    assert proceso.adelantos(base, limpia) == []

    adelantada = mundo.situar(mundo.ilia, mundo.orilla)
    detectadas = proceso.adelantos(base, adelantada)

    assert [r.tipo for r in detectadas] == [TipoDeRestriccion.POSICION_DE_PERSONAJE]
    assert detectadas[0].lugar_id == mundo.orilla


def test_revelar_el_hecho_que_guardaba_una_escena_posterior_es_adelantarse(
    base: Conexion,
) -> None:
    mundo = fabrica.mundo_del_ciclo(base)
    hecho_id = mundo.hecho_descriptivo("el puente hablo la primera noche")
    mundo.encargar([fabrica.revelacion(hecho_id=hecho_id)])

    from app.canon import service as canon

    escena = canon.obtener_hecho(base, hecho_id).escena_id
    detectadas = proceso.adelantos(base, escena)

    assert [r.tipo for r in detectadas] == [TipoDeRestriccion.REVELACION]


def test_seguir_vivo_no_adelanta_un_destino_de_terminar_vivo(base: Conexion) -> None:
    """La asimetria del estado final, que es donde esta el falso positivo facil.

    Que el personaje siga vivo hoy no adelanta nada: le quedan todas las escenas
    para morirse. Muerto, en cambio, no vuelve.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.encargar([fabrica.estado_final(mundo.ilia, "vivo")])

    escena = mundo.escena_consolidada()

    assert proceso.adelantos(base, escena) == []


def test_matar_antes_de_tiempo_a_quien_debia_morir_al_final_si_adelanta(
    base: Conexion,
) -> None:
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.encargar([fabrica.estado_final(mundo.ilia, "muerto")])

    muerte = mundo.matar(mundo.ilia)

    assert [r.valor for r in proceso.adelantos(base, muerte)] == ["muerto"]


def test_una_restriccion_sin_columnas_cotejables_no_produce_falsos_positivos(
    base: Conexion,
) -> None:
    """Una restriccion que solo trae prosa no se puede comprobar.

    No se adivina: cuenta en el denominador de la deriva y en nada mas. Es el
    precio declarado de que `alcance` no tenga contenido especificado.
    """
    mundo = fabrica.mundo_del_ciclo(base)
    mundo.encargar(
        [
            process_schemas.NuevaRestriccion(
                tipo=TipoDeRestriccion.ESTADO_FINAL,
                enunciado="que se note la tension entre ambos",
            )
        ]
    )

    escena = mundo.situar(mundo.ilia, mundo.orilla)

    assert proceso.adelantos(base, escena) == []
