"""Validadores del rol editor que cuentan hasta cero: `invencion_destinatario` y
`temas_excluidos` (RF-QUA-06, D-13; O-20, O-21).

Salen de la única llamada del judge: sus campos `afirmaciones_destinatario` y
`temas_excluidos`. La mitad programática de `invencion_destinatario` coteja cada afirmación
contra el brief y el texto libre; ambos cierran el paso siempre, porque su umbral es cero.
"""

from __future__ import annotations

import pytest

from app.commons.config import cargar_config
from app.process.judge import juzgar
from app.quality.judge import evaluar_judge
from app.quality.models import ContextoJudge, ResultadoValidador
from app.quality.registro import comprobar
from tests.arquitectura.comprobadores import RAIZ_REPO
from tests.conftest import Entorno
from tests.fixtures.borradores import prosa
from tests.fixtures.judge import salida_judge
from tests.fixtures.planificada import novela_planificada

CONFIG = cargar_config(RAIZ_REPO / "config")
INVENTADA = "Marta trabaja de cirujana en el hospital del puerto desde hace diez años."
HOSPITAL = "Pasó aquel invierno ingresada, entre sueros y visitas cortas."
TEXTO = prosa(1200, extra=f"{INVENTADA} {HOSPITAL} Aprendió a navegar en un barco llamado Alondra.")
CONTEXTO = ContextoJudge(
    destinatario="Marta",
    soporte=[
        "tozuda",
        "le encanta el mar",
        "el verano en que aprendió a navegar",
        "Aprendió a navegar en un barco llamado Alondra",
        "Tiene un perro",
    ],
    temas_excluidos=["enfermedad"],
    texto=TEXTO,
)


def _salida(
    afirmaciones: list[dict[str, str]], temas: list[dict[str, object]]
) -> dict[str, object]:
    salida = salida_judge()
    salida["afirmaciones_destinatario"] = afirmaciones
    salida["temas_excluidos"] = temas
    return salida


def _por_nombre(resultados: list[ResultadoValidador], nombre: str) -> ResultadoValidador:
    return next(v for v in resultados if v.nombre == nombre)


def test_un_hecho_personal_ausente_del_brief_cuenta_uno_y_se_cita() -> None:
    salida = _salida(
        [
            {"afirmacion": "Marta es cirujana en un hospital", "fragmento": INVENTADA},
            {
                "afirmacion": "Marta aprendió a navegar en el Alondra",
                "fragmento": "Aprendió a navegar en un barco llamado Alondra.",
            },
        ],
        [],
    )
    r = evaluar_judge(CONFIG, salida, None, CONTEXTO)
    v = _por_nombre(r.todos, "invencion_destinatario")
    comprobar(v)
    assert v.valor == 1 and not v.pasa and v.cierra_el_paso
    assert "cirujana" in v.detalle
    [defecto] = v.defectos
    assert defecto.gravedad == "alta" and INVENTADA[:30] in defecto.descripcion


def test_una_cita_que_no_esta_en_el_capitulo_no_cuenta() -> None:
    salida = _salida([{"afirmacion": "Marta es piloto", "fragmento": "Marta pilotaba aviones"}], [])
    v = _por_nombre(evaluar_judge(CONFIG, salida, None, CONTEXTO).todos, "invencion_destinatario")
    assert v.valor == 0 and v.pasa


def test_un_tema_excluido_que_aparece_falla_aunque_no_se_nombre() -> None:
    salida = _salida([], [{"tema": "enfermedad", "aparece": True, "fragmento": HOSPITAL}])
    v = _por_nombre(evaluar_judge(CONFIG, salida, None, CONTEXTO).todos, "temas_excluidos")
    comprobar(v)
    assert v.valor == 1 and not v.pasa and v.cierra_el_paso
    assert "enfermedad" in v.detalle
    assert "enfermedad" not in TEXTO.lower()  # ninguna palabra lo nombra


def test_un_tema_que_no_aparece_o_no_esta_excluido_no_cuenta() -> None:
    salida = _salida(
        [],
        [
            {"tema": "enfermedad", "aparece": False, "fragmento": ""},
            {"tema": "política", "aparece": True, "fragmento": HOSPITAL},
        ],
    )
    v = _por_nombre(evaluar_judge(CONFIG, salida, None, CONTEXTO).todos, "temas_excluidos")
    assert v.valor == 0 and v.pasa


@pytest.mark.parametrize("cerrar", [False, True])
def test_los_dos_cierran_el_paso_en_medicion_y_fuera(cerrar: bool) -> None:
    u = CONFIG.umbrales
    config = CONFIG.model_copy(
        update={
            "umbrales": u.model_copy(
                update={"medicion": u.medicion.model_copy(update={"cerrar_el_paso": cerrar})}
            )
        }
    )
    r = evaluar_judge(config, _salida([], []), None, CONTEXTO)
    for nombre in ("invencion_destinatario", "temas_excluidos"):
        assert _por_nombre(r.todos, nombre).cierra_el_paso


@pytest.mark.anyio
async def test_el_ciclo_emite_los_dos_scores_con_el_brief_como_soporte(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    entorno.modelo.encolar(
        "judge",
        _salida(
            [{"afirmacion": "Marta es cirujana", "fragmento": INVENTADA}],
            [{"tema": "enfermedad", "aparece": True, "fragmento": HOSPITAL}],
        ),
    )
    r = await juzgar(
        entorno.recursos, novel_id=novela, version=1, numero=1, titulo="t", texto=TEXTO
    )
    assert _por_nombre(r.todos, "invencion_destinatario").valor == 1
    assert _por_nombre(r.todos, "temas_excluidos").valor == 1
    assert [s.valor for s in entorno.trazas.scores_de("invencion_destinatario")] == [1.0]
    assert [s.valor for s in entorno.trazas.scores_de("temas_excluidos")] == [1.0]


@pytest.mark.anyio
async def test_lo_que_dice_el_brief_no_es_invencion_aunque_no_sea_rasgo_ni_recuerdo(
    entorno: Entorno,
) -> None:
    # Humo adversarial real del P38: la edad, la ocasión y quién regala vienen del brief, y
    # contarlas como invención suspendía el capítulo en todos los intentos.
    novela = await novela_planificada(entorno)
    edad = "Marta cumple treinta y cuatro años este otoño."
    hermana = "Su hermana le había escrito para el cumpleaños."
    texto = prosa(1200, extra=f"{edad} {hermana}")
    entorno.modelo.encolar(
        "judge",
        _salida(
            [
                {"afirmacion": "Marta cumple treinta y cuatro años", "fragmento": edad},
                {"afirmacion": "Marta tiene una hermana que le escribe", "fragmento": hermana},
                {"afirmacion": "Celebra su cumpleaños", "fragmento": hermana},
            ],
            [],
        ),
    )
    r = await juzgar(
        entorno.recursos, novel_id=novela, version=1, numero=1, titulo="t", texto=texto
    )
    v = _por_nombre(r.todos, "invencion_destinatario")
    assert v.valor == 0 and v.pasa, v.detalle
