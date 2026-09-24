"""Estado de versión y gate sobre la candidata (P47a, RF-QUA-03, RNF-19, TO-045).

Una versión nace `candidata` al aceptarse el último capítulo; el gate completo, con
`render_visual`, corre sobre ella; pasa a `publicada` solo si todos pasan y, si no, queda
`rechazada`. La vigente, el listado y el export ven solo las `publicadas`.
"""

from __future__ import annotations

import sqlite3
import uuid
from functools import partial
from typing import Any

import pytest

from app.novel import service as novel
from app.versioning import confirmar
from app.versioning import service as versioning
from app.versioning.render_visual import SinNavegador
from tests.conftest import Entorno, Instancia, ValidarContrato
from tests.dobles.guiones import guion_completo
from tests.fixtures.briefs import brief_ejemplo
from tests.fixtures.planificada import generar_entera
from tests.process.test_orquestador import esperar
from tests.versioning.test_confirmar import _publicada, _solicitud


def _sql(entorno: Entorno, sql: str, *parametros: Any) -> None:
    def escribir(con: sqlite3.Connection) -> None:
        con.execute(sql, parametros)

    entorno.recursos.db.ejecutar_sync(escribir)


def _estados(entorno: Entorno, novela: str) -> list[tuple[int, str]]:
    filas = entorno.consultar(
        "SELECT version, estado FROM version_novela WHERE novel_id = ? ORDER BY version", novela
    )
    return [(f["version"], f["estado"]) for f in filas]


async def _vigente(entorno: Entorno, novela: str) -> int | None:
    return await entorno.recursos.db.ejecutar(partial(novel.version_vigente, novel_id=novela))


# --- Esquema ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_el_esquema_solo_admite_candidata_a_publicada_o_rechazada(entorno: Entorno) -> None:
    guion_completo(entorno.modelo)
    novela, _ = await generar_entera(entorno)
    assert _estados(entorno, novela) == [(1, "publicada")]

    # Una publicada no vuelve atrás ni cambia de contenido.
    for sql in (
        "UPDATE version_novela SET estado = 'rechazada' WHERE novel_id = ?",
        "UPDATE version_novela SET estado = 'candidata' WHERE novel_id = ?",
        "UPDATE version_novela SET hash = 'otro' WHERE novel_id = ?",
        "DELETE FROM version_novela WHERE novel_id = ?",
    ):
        with pytest.raises(sqlite3.IntegrityError):
            _sql(entorno, sql, novela)

    # Una candidata pasa a publicada o a rechazada, una sola vez y sin tocar su contenido.
    for destino in ("publicada", "rechazada"):
        vid = str(uuid.uuid4())
        _sql(
            entorno,
            "INSERT INTO version_novela (id, novel_id, version, hash, publicada_en, estado)"
            " VALUES (?, ?, (SELECT max(version) + 1 FROM version_novela WHERE novel_id = ?),"
            " 'h', '2026-09-24T00:00:00Z', 'candidata')",
            vid,
            novela,
            novela,
        )
        with pytest.raises(sqlite3.IntegrityError):
            _sql(entorno, "UPDATE version_novela SET hash = 'otro' WHERE id = ?", vid)
        _sql(entorno, "UPDATE version_novela SET estado = ? WHERE id = ?", destino, vid)
        with pytest.raises(sqlite3.IntegrityError):
            _sql(entorno, "UPDATE version_novela SET estado = 'candidata' WHERE id = ?", vid)

    with pytest.raises(sqlite3.IntegrityError):
        _sql(
            entorno,
            "INSERT INTO version_novela (id, novel_id, version, hash, publicada_en, estado)"
            " VALUES (?, ?, 9, 'h', '2026-09-24T00:00:00Z', 'borrador')",
            str(uuid.uuid4()),
            novela,
        )


def test_la_migracion_marca_publicadas_las_versiones_que_ya_existian(entorno: Entorno) -> None:
    """A-112: la columna nueva vale `publicada` para las filas que no dicen otra cosa."""
    [(defecto,)] = entorno.consultar(
        "SELECT dflt_value FROM pragma_table_info('version_novela') WHERE name = 'estado'"
    )
    assert defecto == "'publicada'"


# --- Gate sobre la candidata ----------------------------------------------------------


@pytest.mark.anyio
async def test_el_gate_pinta_la_candidata_y_despues_la_publica(entorno: Entorno) -> None:
    vistas: list[tuple[str, int, int | None]] = []

    async def mirar(novela: str, version: int) -> None:
        v = await versioning.obtener_version(entorno.recursos.db, novela, version)
        vistas.append((v.estado, len(v.capitulos), await _vigente(entorno, novela)))

    entorno.render.al_pintar = mirar
    guion_completo(entorno.modelo)
    novela, _ = await generar_entera(entorno)

    assert vistas == [("candidata", 10, None)]
    assert entorno.render.pintadas == [(novela, 1)]
    assert _estados(entorno, novela) == [(1, "publicada")]
    assert await _vigente(entorno, novela) == 1
    [resumen] = await versioning.listar_versiones(entorno.recursos.db, novela)
    assert resumen.version == 1
    assert [s.valor for s in entorno.trazas.scores_de("render_visual")] == [1.0]


@pytest.mark.anyio
async def test_render_visual_en_rojo_deja_la_version_rechazada(entorno: Entorno) -> None:
    entorno.render.pasa = False
    guion_completo(entorno.modelo)
    novela, gid = await generar_entera(entorno)

    assert _estados(entorno, novela) == [(1, "rechazada")]
    assert entorno.consultar("SELECT estado FROM obra WHERE novel_id = ?", novela)[0][0] == (
        "Detenida"
    )
    t = entorno.consultar("SELECT * FROM trabajo WHERE id = ?", gid)[0]
    assert t["version_resultante"] is None and t["detenida_por"] == "error-interno"
    assert await _vigente(entorno, novela) is None
    assert await versioning.listar_versiones(entorno.recursos.db, novela) == []
    v = await versioning.obtener_version(entorno.recursos.db, novela, 1)
    assert v.estado == "rechazada" and len(v.capitulos) == 10
    assert [s.valor for s in entorno.trazas.scores_de("render_visual")] == [0.0]
    detencion = entorno.consultar(
        "SELECT entrada FROM audit_log WHERE novel_id = ? AND resultado = 'detener'", novela
    )
    assert any("render_visual" in f["entrada"] for f in detencion)


@pytest.mark.anyio
async def test_sin_navegador_ninguna_version_se_publica(entorno: Entorno) -> None:
    """A-114: la implementación de producción sin servidor MCP falla con el motivo."""
    veredicto = await SinNavegador()(novel_id=str(uuid.uuid4()), version=1)
    assert not veredicto.pasa and veredicto.nombre == "render_visual"
    assert "PLAYWRIGHT_MCP_URL" in veredicto.detalle


@pytest.mark.anyio
async def test_una_dirigida_rechazada_deja_vigente_la_anterior(entorno: Entorno) -> None:
    novela = await _publicada(entorno)
    sid, _ = await _solicitud(entorno, novela)
    g = await confirmar.confirmar(entorno.recursos, novela, sid)
    entorno.render.pasa = False
    await entorno.orquestador().ejecutar(str(g.generacion_id))

    assert _estados(entorno, novela) == [(1, "publicada"), (2, "rechazada")]
    assert await _vigente(entorno, novela) == 1
    assert [r.version for r in await versioning.listar_versiones(entorno.recursos.db, novela)] == [
        1
    ]
    [fila] = entorno.consultar("SELECT estado FROM solicitud_cambio WHERE id = ?", sid)
    assert fila["estado"] != "aplicada"


@pytest.mark.anyio
async def test_una_reanudacion_reutiliza_la_candidata(entorno: Entorno) -> None:
    """A-115: proponer dos veces la misma versión no la duplica ni falla."""
    entorno.render.pasa = False
    guion_completo(entorno.modelo)
    novela, gid = await generar_entera(entorno)
    publicador = entorno.orquestador().publicador

    def proponer_otra_vez(con: sqlite3.Connection) -> str:
        return publicador.proponer(con, novel_id=novela, version=1, generacion_id=gid)

    with pytest.raises(Exception, match="rechazada"):
        await entorno.recursos.db.en_transaccion(proponer_otra_vez)

    # Una candidata viva, en cambio, se reutiliza tal cual.
    vid = str(uuid.uuid4())
    _sql(
        entorno,
        "INSERT INTO version_novela (id, novel_id, version, hash, publicada_en, estado)"
        " VALUES (?, ?, 2, 'h', '2026-09-24T00:00:00Z', 'candidata')",
        vid,
        novela,
    )

    def proponer_la_2(con: sqlite3.Connection) -> str:
        return publicador.proponer(con, novel_id=novela, version=2, generacion_id=gid)

    assert await entorno.recursos.db.en_transaccion(proponer_la_2) == "h"
    assert _estados(entorno, novela) == [(1, "rechazada"), (2, "candidata")]


# --- HTTP ------------------------------------------------------------------------------


def test_la_candidata_rechazada_se_lee_por_su_numero_y_no_es_la_vigente(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    instancia.render.pasa = False
    guion_completo(instancia.modelo)
    novela = instancia.cliente.post("/novelas", json=brief_ejemplo()).json()["novel_id"]
    gid = instancia.cliente.post(f"/novelas/{novela}/generaciones").json()["generacion_id"]
    g = esperar(instancia.cliente, novela, gid, lambda g: g["es_terminal"])
    assert g["estado"] == "Detenida"

    r = instancia.cliente.get(f"/novelas/{novela}/versiones/1")
    validar_contra_contrato(r, "obtenerVersion")
    assert r.status_code == 200 and r.json()["estado"] == "rechazada"
    r = instancia.cliente.get(f"/novelas/{novela}/versiones/1/capitulos")
    assert r.status_code == 200 and len(r.json()) == 10

    r = instancia.cliente.get(f"/novelas/{novela}/versiones")
    validar_contra_contrato(r, "listarVersiones")
    assert r.json() == []
    r = instancia.cliente.get(f"/novelas/{novela}")
    validar_contra_contrato(r, "obtenerNovela")
    assert r.json().get("version_vigente") is None
