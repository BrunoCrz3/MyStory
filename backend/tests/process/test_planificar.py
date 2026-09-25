"""Planificador: el esquema de la obra (RF-NOVEL-01, D-23)."""

from __future__ import annotations

import pytest

from app.commons.errores import LimiteDeIntentosAgotado
from app.process.planificar import planificar
from tests.conftest import Entorno
from tests.fixtures.briefs import brief_ejemplo
from tests.fixtures.esquemas import con_cambios, esquema_valido


@pytest.mark.anyio
async def test_un_esquema_valido_crea_los_capitulos_y_fija_el_titulo(entorno: Entorno) -> None:
    novela = await entorno.crear_novela(brief_ejemplo())
    entorno.modelo.encolar("planificador", esquema_valido(brief_ejemplo()))
    esquema = await planificar(entorno.recursos, novel_id=novela, version=1)
    assert esquema.titulo == "El verano del Alondra"

    filas = entorno.consultar(
        "SELECT numero, estado, version FROM capitulo WHERE novel_id = ? ORDER BY numero", novela
    )
    assert [(f["numero"], f["estado"], f["version"]) for f in filas] == [
        (n, "Pendiente", 1) for n in range(1, 11)
    ]
    assert (
        entorno.consultar("SELECT titulo FROM obra WHERE novel_id = ?", novela)[0]["titulo"]
        == "El verano del Alondra"
    )
    restricciones = entorno.consultar(
        "SELECT r.numero, r.tipo, b.pov FROM restriccion_destino r"
        " JOIN brief_capitulo b ON b.restriccion_id = r.id WHERE r.novel_id = ? ORDER BY r.numero",
        novela,
    )
    assert len(restricciones) == 10
    destinataria = entorno.consultar(
        "SELECT nombre FROM personaje WHERE novel_id = ? AND es_destinatario = 1", novela
    )
    assert [d["nombre"] for d in destinataria] == [brief_ejemplo()["destinatario"]["nombre"]]


@pytest.mark.anyio
async def test_numero_de_capitulos_equivocado_se_reintenta(entorno: Entorno) -> None:
    novela = await entorno.crear_novela(brief_ejemplo())
    malo = esquema_valido(brief_ejemplo(), capitulos=9)
    entorno.modelo.encolar("planificador", malo, esquema_valido(brief_ejemplo()))
    await planificar(entorno.recursos, novel_id=novela, version=1)
    assert entorno.modelo.llamadas["planificador"] == 2
    segundo = entorno.modelo.peticiones[-1].mensajes[0].contenido
    assert "10 capítulos" in segundo and "9" in segundo  # el reintento lleva el porqué
    assert [s.valor for s in entorno.trazas.scores_de("schema_valido")] == [0.0, 1.0]


@pytest.mark.anyio
async def test_alcance_con_entidad_inexistente_falla_schema_valido(entorno: Entorno) -> None:
    novela = await entorno.crear_novela(brief_ejemplo())
    malo = esquema_valido(brief_ejemplo())
    malo["capitulos"][3]["restriccion"]["alcance"].append({"tipo": "personaje", "nombre": "Nadie"})
    limite = entorno.recursos.config.umbrales.orquestacion.max_intentos_capitulo
    entorno.modelo.encolar("planificador", *([malo] * (limite + 1)))
    with pytest.raises(LimiteDeIntentosAgotado, match="Nadie"):
        await planificar(entorno.recursos, novel_id=novela, version=1)
    assert entorno.modelo.llamadas["planificador"] == limite + 1
    assert (
        entorno.consultar("SELECT count(*) AS n FROM capitulo WHERE novel_id = ?", novela)[0]["n"]
        == 0
    )


@pytest.mark.anyio
async def test_elemento_obligatorio_fuera_del_plan_falla(entorno: Entorno) -> None:
    novela = await entorno.crear_novela(brief_ejemplo())
    malo = esquema_valido(brief_ejemplo())
    for capitulo in malo["capitulos"]:
        capitulo["elementos"] = []
    entorno.modelo.encolar("planificador", malo, esquema_valido(brief_ejemplo()))
    await planificar(entorno.recursos, novel_id=novela, version=1)
    assert "obligatorio" in entorno.modelo.peticiones[-1].mensajes[0].contenido


@pytest.mark.anyio
async def test_destinatario_mal_escrito_falla(entorno: Entorno) -> None:
    novela = await entorno.crear_novela(brief_ejemplo())
    malo = esquema_valido(brief_ejemplo())
    malo["personajes"][0]["nombre"] = "Ondinna"
    entorno.modelo.encolar("planificador", malo, esquema_valido(brief_ejemplo()))
    await planificar(entorno.recursos, novel_id=novela, version=1)
    assert entorno.modelo.llamadas["planificador"] == 2


@pytest.mark.anyio
async def test_salida_que_no_cumple_el_schema_falla_schema_valido(entorno: Entorno) -> None:
    novela = await entorno.crear_novela(brief_ejemplo())
    entorno.modelo.encolar(
        "planificador",
        con_cambios(esquema_valido(brief_ejemplo()), capitulos="diez"),
        esquema_valido(brief_ejemplo()),
    )
    await planificar(entorno.recursos, novel_id=novela, version=1)
    assert [s.valor for s in entorno.trazas.scores_de("schema_valido")] == [0.0, 1.0]


@pytest.mark.anyio
async def test_la_llamada_abre_el_span_planner_con_la_story_bible(entorno: Entorno) -> None:
    novela = await entorno.crear_novela(brief_ejemplo())
    entorno.modelo.encolar("planificador", esquema_valido(brief_ejemplo()))
    await planificar(entorno.recursos, novel_id=novela, version=1)
    assert "planner" in entorno.trazas.nombres("generacion")
    assert "consultar_story_bible" in entorno.trazas.nombres("span")
    peticion = entorno.modelo.peticiones[0]
    assert peticion.esquema_salida is not None
    assert brief_ejemplo()["destinatario"]["nombre"] in peticion.mensajes[0].contenido
    assert brief_ejemplo()["destinatario"]["nombre"] not in peticion.system
