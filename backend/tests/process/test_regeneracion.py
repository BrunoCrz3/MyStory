"""Regeneración dirigida y publicación de la versión nueva (RF-VER-08, RF-VER-02, RF-VER-03,
D-05, D-17): solo se reescriben los capítulos obsoletos, la versión nueva comparte fila con los
no afectados, y la anterior se conserva entera con su hash."""

from __future__ import annotations

import sqlite3
from typing import Any

import pytest

from app.commons.llm import Peticion
from app.process import cola
from app.versioning import confirmar
from app.versioning import service as versioning
from app.versioning.gate import regeneracion_fiel
from tests.conftest import Entorno
from tests.dobles.guiones import numero_de_la_tarea, redactar
from tests.fixtures.borradores import borrador
from tests.versioning.test_confirmar import _publicada, _solicitud

NUEVO = "El perro se llama Nala"


def _redactor_que_lee_el_cambio(p: Peticion) -> dict[str, str]:
    """Un redactor que, si el contexto trae el hecho nuevo, escribe otro texto."""
    if NUEVO in p.mensajes[0].contenido:
        n = numero_de_la_tarea(p)
        return borrador(titulo=f"Capítulo {n}: Nala", extra=f"{NUEVO}, y ladró al verla llegar.")
    return redactar(p)


async def _regenerada(e: Entorno) -> tuple[str, str, Any]:
    novela = await _publicada(e)
    hash_v1 = await e.recursos.db.ejecutar(
        lambda con: versioning.hash_de_version(con, novel_id=novela, version=1)
    )
    sid, viejo = await _solicitud(e, novela)
    e.modelo.por_defecto["redactor"] = _redactor_que_lee_el_cambio
    antes = e.modelo.llamadas["redactor"]
    g = await confirmar.confirmar(e.recursos, novela, sid)
    await e.orquestador().ejecutar(str(g.generacion_id))
    assert e.modelo.llamadas["redactor"] - antes == 2
    return novela, hash_v1, viejo


def _vinculos(e: Entorno, novela: str, version: int) -> dict[int, str]:
    filas = e.consultar(
        "SELECT numero, capitulo_id FROM version_capitulo WHERE novel_id = ? AND version = ?",
        novela,
        version,
    )
    return {f["numero"]: f["capitulo_id"] for f in filas}


@pytest.mark.anyio
async def test_solo_se_reescriben_los_obsoletos_y_se_publica_la_version_2(
    entorno: Entorno,
) -> None:
    novela, hash_v1, _ = await _regenerada(entorno)

    [generacion] = [
        g for g in await cola.listar_generaciones(entorno.recursos, novela) if g.tipo == "dirigida"
    ]
    assert generacion.estado == "Publicada" and generacion.version_resultante == 2
    [obra] = entorno.consultar("SELECT estado FROM obra WHERE novel_id = ?", novela)
    assert obra["estado"] == "Publicada"

    v1, v2 = _vinculos(entorno, novela, 1), _vinculos(entorno, novela, 2)
    assert sorted(v2) == list(range(1, 11))
    assert {n for n in v2 if v2[n] != v1[n]} == {2, 7}  # la misma fila para los no afectados

    capitulos = await versioning.listar_capitulos(entorno.recursos.db, novela, 2)
    assert {c.numero for c in capitulos if c.modificado} == {2, 7}
    assert all(NUEVO in (c.texto or "") for c in capitulos if c.numero in (2, 7))
    assert all(NUEVO not in (c.texto or "") for c in capitulos if c.numero not in (2, 7))

    # La versión 1 sigue entera: mismo hash, mismos textos, y lee el hecho viejo.
    assert (
        await entorno.recursos.db.ejecutar(
            lambda con: versioning.hash_de_version(con, novel_id=novela, version=1)
        )
        == hash_v1
    )
    capitulos_v1 = await versioning.listar_capitulos(entorno.recursos.db, novela, 1)
    assert all(NUEVO not in (c.texto or "") for c in capitulos_v1)

    [s] = entorno.consultar("SELECT estado, version_resultante FROM solicitud_cambio")
    assert (s["estado"], s["version_resultante"]) == ("aplicada", 2)


@pytest.mark.anyio
async def test_el_contexto_de_la_reescritura_lleva_el_snapshot_de_la_version_2(
    entorno: Entorno,
) -> None:
    _, _, viejo = await _regenerada(entorno)
    reescrituras = [
        p
        for p in entorno.modelo.peticiones
        if p.rol == "redactor" and NUEVO in p.mensajes[0].contenido
    ]
    assert len(reescrituras) == 2
    septimo = reescrituras[-1].mensajes[0].contenido
    estado = septimo.split('<capa nombre="estado">', 1)[1].split("</capa>", 1)[0]
    assert NUEVO in estado
    assert viejo.enunciado not in estado


@pytest.mark.anyio
async def test_regeneracion_fiel_pasa_con_lo_publicado_y_falla_sin_base_publicada(
    entorno: Entorno,
) -> None:
    novela, _, _ = await _regenerada(entorno)

    def comprobar(version: int) -> Any:
        def leer(con: sqlite3.Connection) -> Any:
            candidatos = versioning.candidatos(con, novel_id=novela, version=version)
            return regeneracion_fiel(con, novel_id=novela, version=version, candidatos=candidatos)

        return entorno.recursos.db.ejecutar_sync(leer)

    assert comprobar(2).pasa
    # TO-062: la base es la publicada más alta por debajo, no la de número anterior; la 4 parte
    # de la 2 aunque la 3 no exista (una rechazada conserva su número).
    assert comprobar(4).pasa
    fallo = comprobar(1)  # por debajo de la 1 no hay ninguna publicada
    assert not fallo.pasa and "no parte de ninguna versión publicada" in fallo.detalle


@pytest.mark.anyio
async def test_regeneracion_fiel_falla_si_cambia_un_capitulo_no_afectado(
    entorno: Entorno,
) -> None:
    novela, _, _ = await _regenerada(entorno)
    v2 = _vinculos(entorno, novela, 2)

    def leer(con: sqlite3.Connection) -> Any:
        candidatos = dict(v2)
        candidatos[5] = candidatos[2]  # como si el 5, que no estaba obsoleto, hubiera cambiado
        return regeneracion_fiel(con, novel_id=novela, version=3, candidatos=candidatos)

    # Sobre la 3 no hay obsoletos: cualquier cambio respecto de la 2 es infiel.
    resultado = entorno.recursos.db.ejecutar_sync(leer)
    assert not resultado.pasa and "5" in resultado.detalle
