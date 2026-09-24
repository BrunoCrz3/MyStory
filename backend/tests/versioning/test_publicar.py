"""Gate mínimo de F1 y publicación inmutable (RF-VER-01, RF-VER-03, RF-QUA-03, RNF-07, D-05,
D-17)."""

from __future__ import annotations

import re
import sqlite3
from functools import partial

import pytest

from app.versioning import service as versioning
from tests.conftest import Entorno
from tests.dobles.guiones import extraer, guion_completo
from tests.fixtures.borradores import borrador
from tests.fixtures.planificada import generar_entera


def _obra(entorno: Entorno, novela: str) -> str:
    return str(entorno.consultar("SELECT estado FROM obra WHERE novel_id = ?", novela)[0][0])


@pytest.mark.anyio
async def test_con_el_gate_en_verde_se_publica_la_version_1(entorno: Entorno) -> None:
    guion_completo(entorno.modelo)
    novela, gid = await generar_entera(entorno)

    assert _obra(entorno, novela) == "Publicada"
    t = entorno.consultar("SELECT * FROM trabajo WHERE id = ?", gid)[0]
    assert (t["estado"], t["estado_cola"], t["version_resultante"]) == ("Publicada", "terminado", 1)
    assert t["terminada_en"] is not None
    v = entorno.consultar("SELECT * FROM version_novela WHERE novel_id = ?", novela)
    assert len(v) == 1
    assert v[0]["version"] == 1 and v[0]["version_anterior_id"] is None
    assert re.fullmatch(r"[0-9a-f]{64}", v[0]["hash"])
    vinculos = entorno.consultar(
        "SELECT numero, modificado FROM version_capitulo WHERE novel_id = ? AND version = 1"
        " ORDER BY numero",
        novela,
    )
    assert [f["numero"] for f in vinculos] == list(range(1, 11))
    assert all(f["modificado"] == 0 for f in vinculos)
    for nombre in ("estructura_edicion", "elementos_obligatorios"):
        assert [s.valor for s in entorno.trazas.scores_de(nombre)] == [1.0]
    assert "gate_publicacion" in entorno.trazas.nombres() and "publicar" in entorno.trazas.nombres()


@pytest.mark.anyio
async def test_un_elemento_obligatorio_ausente_no_publica(entorno: Entorno) -> None:
    guion_completo(entorno.modelo)
    entorno.modelo.por_defecto["extractor"] = partial(extraer, elementos=[])
    novela, gid = await generar_entera(entorno)

    assert _obra(entorno, novela) == "Detenida"
    # TO-045: la versión existió como candidata y queda rechazada, nunca publicada.
    versiones = entorno.consultar("SELECT estado FROM version_novela WHERE novel_id = ?", novela)
    assert [f["estado"] for f in versiones] == ["rechazada"]
    t = entorno.consultar("SELECT * FROM trabajo WHERE id = ?", gid)[0]
    assert t["version_resultante"] is None and t["detenida_por"] == "error-interno"
    assert [s.valor for s in entorno.trazas.scores_de("elementos_obligatorios")] == [0.0]
    detencion = entorno.consultar(
        "SELECT entrada FROM audit_log WHERE novel_id = ? AND resultado = 'detener'", novela
    )
    assert any("elementos_obligatorios" in f["entrada"] for f in detencion)


@pytest.mark.anyio
async def test_titulos_repetidos_no_pasan_estructura_edicion(entorno: Entorno) -> None:
    guion_completo(entorno.modelo)
    entorno.modelo.por_defecto["redactor"] = lambda p: borrador(titulo="Siempre el mismo")
    novela, _ = await generar_entera(entorno)
    assert _obra(entorno, novela) == "Detenida"
    assert [s.valor for s in entorno.trazas.scores_de("estructura_edicion")] == [0.0]


@pytest.mark.anyio
async def test_una_version_publicada_no_cambia_y_su_hash_se_recalcula_igual(
    entorno: Entorno,
) -> None:
    guion_completo(entorno.modelo)
    novela, _ = await generar_entera(entorno)
    guardado = entorno.consultar("SELECT hash FROM version_novela WHERE novel_id = ?", novela)[0][0]
    recalculado = entorno.recursos.db.ejecutar_sync(
        partial(versioning.hash_de_version, novel_id=novela, version=1)
    )
    assert recalculado == guardado

    intentos = [
        "UPDATE version_novela SET hash = 'x' WHERE novel_id = ?",
        "DELETE FROM version_novela WHERE novel_id = ?",
        "UPDATE version_capitulo SET modificado = 1 WHERE novel_id = ?",
        "DELETE FROM version_capitulo WHERE novel_id = ?",
        "UPDATE capitulo SET texto = 'otro' WHERE novel_id = ? AND numero = 1",
        "UPDATE capitulo SET titulo = 'otro' WHERE novel_id = ? AND numero = 1",
    ]

    def ejecutar(con: sqlite3.Connection, sql: str) -> None:
        con.execute(sql, (novela,))

    for sql in intentos:
        with pytest.raises(sqlite3.IntegrityError):
            entorno.recursos.db.ejecutar_sync(partial(ejecutar, sql=sql))
    assert (
        entorno.recursos.db.ejecutar_sync(
            partial(versioning.hash_de_version, novel_id=novela, version=1)
        )
        == guardado
    )


@pytest.mark.anyio
async def test_el_capitulo_publicado_puede_cambiar_de_estado(entorno: Entorno) -> None:
    """El retcon marca `Obsoleto` un capítulo publicado (F4): el estado no es contenido."""
    guion_completo(entorno.modelo)
    novela, _ = await generar_entera(entorno)
    entorno.recursos.db.ejecutar_sync(
        lambda con: con.execute(
            "UPDATE capitulo SET estado = 'Obsoleto' WHERE novel_id = ? AND numero = 2", (novela,)
        )
    )
