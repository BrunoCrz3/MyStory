"""Judge: los seis criterios de la rúbrica por separado y con justificación, en el modelo del
judge y no en el del redactor (RF-QUA-04, RF-QUA-07, TO-013, D-15)."""

from __future__ import annotations

import pytest

from app.commons.config import Config, cargar_config
from app.policy.service import PolicyEngine, Veredicto
from app.process.judge import juzgar
from app.quality.judge import CRITERIO_A_SCORE, evaluar_judge
from app.quality.registro import comprobar
from tests.arquitectura.comprobadores import RAIZ_REPO
from tests.conftest import Entorno
from tests.fixtures.borradores import borrador
from tests.fixtures.judge import CRITERIOS, salida_judge
from tests.fixtures.planificada import novela_planificada

CONFIG = cargar_config(RAIZ_REPO / "config")
SCORES = [
    "consistencia_factica",
    "adecuacion_tono",
    "cierre_arco",
    "coherencia_personajes",
    "ritmo",
    "personalizacion_natural",
]


def _con_medicion(cerrar: bool) -> Config:
    u = CONFIG.umbrales
    medicion = u.medicion.model_copy(update={"cerrar_el_paso": cerrar})
    return CONFIG.model_copy(update={"umbrales": u.model_copy(update={"medicion": medicion})})


def _suspende(entorno: Entorno, novela: str, resultados: list) -> bool:  # type: ignore[type-arg]
    capitulo_id = entorno.consultar(
        "SELECT id FROM capitulo WHERE novel_id = ? AND numero = 1", novela
    )[0]["id"]
    veredictos = [
        Veredicto(nombre=v.nombre, pasa=v.pasa, cierra_el_paso=v.cierra_el_paso, valor=v.valor)
        for v in resultados
    ]
    decision = entorno.recursos.db.en_transaccion_sync(
        lambda con: PolicyEngine(entorno.recursos.config).decidir_capitulo(
            con,
            novel_id=novela,
            capitulo_id=capitulo_id,
            intentos=0,
            veredictos=veredictos,
            reescrituras_por_guardrail=0,
        )
    )
    return decision.accion != "aceptar"


def test_los_criterios_de_la_rubrica_son_los_seis_scores_del_registro() -> None:
    assert list(CRITERIO_A_SCORE) == list(CRITERIOS)
    assert list(CRITERIO_A_SCORE.values()) == SCORES


def test_seis_puntuaciones_separadas_con_su_justificacion() -> None:
    r = evaluar_judge(CONFIG, salida_judge(tono=0.4), None)
    assert r.schema_valido.pasa
    assert [v.nombre for v in r.criterios] == SCORES
    for v in r.criterios:
        comprobar(v)
        assert v.detalle.startswith("Justificación de ")
    tono = r.criterios[1]
    assert tono.valor == 0.4 and not tono.pasa
    assert tono.defectos[0].dimension == "adecuacion_tono"


@pytest.mark.parametrize("quitar", CRITERIOS)
def test_una_salida_sin_alguno_de_los_seis_falla_schema_valido(quitar: str) -> None:
    salida = salida_judge()
    del salida[quitar]
    r = evaluar_judge(CONFIG, salida, None)
    assert not r.schema_valido.pasa and r.schema_valido.cierra_el_paso
    assert r.criterios == []


@pytest.mark.parametrize(
    "roto",
    [
        {"puntuacion": 1.4, "justificacion": "fuera de rango"},
        {"puntuacion": 0.8, "justificacion": ""},
    ],
)
def test_una_puntuacion_fuera_de_rango_o_sin_justificacion_falla_schema_valido(
    roto: dict[str, object],
) -> None:
    salida = salida_judge()
    salida["ritmo"] = roto
    assert not evaluar_judge(CONFIG, salida, None).schema_valido.pasa


def test_un_error_de_salida_del_modelo_falla_schema_valido() -> None:
    r = evaluar_judge(CONFIG, None, "judge: la salida no es JSON")
    assert not r.schema_valido.pasa and "no es JSON" in r.schema_valido.detalle


@pytest.mark.anyio
async def test_bajo_umbral_suspende_solo_fuera_de_medicion_y_el_booleano_siempre(
    entorno: Entorno,
) -> None:
    novela = await novela_planificada(entorno)
    bajo = salida_judge(tono=0.1)

    en_medicion = evaluar_judge(_con_medicion(False), bajo, None)
    assert not _suspende(entorno, novela, [en_medicion.schema_valido, *en_medicion.criterios])

    calibrado = evaluar_judge(_con_medicion(True), bajo, None)
    assert _suspende(entorno, novela, [calibrado.schema_valido, *calibrado.criterios])

    sin_schema = evaluar_judge(_con_medicion(False), None, "truncada")
    assert _suspende(entorno, novela, [sin_schema.schema_valido])


@pytest.mark.anyio
async def test_juzgar_usa_el_modelo_del_judge_y_deja_un_score_por_criterio(
    entorno: Entorno,
) -> None:
    novela = await novela_planificada(entorno)
    entorno.modelo.encolar("judge", salida_judge(ritmo=0.55))
    texto = borrador()
    r = await juzgar(
        entorno.recursos, novel_id=novela, version=1, numero=1, titulo=texto["titulo"],
        texto=texto["texto"],
    )  # fmt: skip

    peticion = entorno.modelo.peticiones[-1]
    assert peticion.rol == "judge"
    roles = entorno.recursos.config.modelos.roles
    assert roles.judge.id != roles.redactor.id
    assert entorno.trazas.nombres("generacion")[-1] == "judge"
    # El capítulo va como dato, y el texto libre del brief como no confiable.
    mensaje = peticion.mensajes[0].contenido
    assert texto["texto"][:40] in mensaje
    assert "<texto_libre_no_confiable>" in mensaje

    assert [v.nombre for v in r.criterios] == SCORES
    for nombre in SCORES:
        [score] = entorno.trazas.scores_de(nombre)
        assert score.comentario and score.comentario.startswith("Justificación de ")
    assert entorno.trazas.scores_de("ritmo")[0].valor == 0.55
    assert [s.valor for s in entorno.trazas.scores_de("schema_valido")] == [1.0]
