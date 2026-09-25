"""Una regeneración fallida no modifica ninguna versión publicada (TO-062).

Decisión del desarrollador tras el ensayo de la demo: la candidata de la regeneración queda
`rechazada`, la novela sigue `Publicada` con su versión vigente intacta y admite solicitudes
nuevas —`Detenida` es un estado de la generación, no de la novela publicada—, las marcas de
`Obsoleto` viven solo en la candidata, y la solicitud siguiente parte de la vigente.

La novela es la del P39: el capítulo 7 usa el hecho que estableció el 2, así que cambiar ese
hecho reescribe el 2 y el 7.
"""

from __future__ import annotations

import uuid
from functools import partial
from typing import Any

import pytest

from app.canon import service as canon
from app.commons.llm import Peticion
from app.process import cola
from app.versioning import confirmar, solicitud
from app.versioning.schemas import NuevaSolicitudCambio
from tests.canon.test_hechos_por_version import _extraer
from tests.conftest import Entorno
from tests.dobles.guiones import corregido, numero_de_la_tarea, redactar
from tests.fixtures.borradores import borrador
from tests.versioning.test_confirmar import _publicada

NALA = "El perro se llama Nala"
DEL_DOS = "En el capítulo 102"


def _falla_el(numero: int):  # type: ignore[no-untyped-def]
    """Un redactor que escribe corto el capítulo `numero` —y un editor que no lo arregla—, así
    que ese capítulo agota sus intentos; los demás se escriben bien."""

    def redactor(p: Peticion) -> dict[str, str]:
        return borrador(300) if numero_de_la_tarea(p) == numero else redactar(p)

    return redactor


async def _confirmar(e: Entorno, novela: str, enunciado: str = NALA) -> Any:
    hechos = await e.recursos.db.ejecutar(
        lambda con: canon.hechos_vigentes(con, novel_id=novela, version=1)
    )
    del_dos = next(h for h in hechos if h.capitulo_establece == 2)
    s = await solicitud.crear_solicitud(
        e.recursos.db,
        e.recursos.config,
        novela,
        NuevaSolicitudCambio(
            hecho_id=uuid.UUID(del_dos.hecho_id), enunciado_nuevo=enunciado, capitulo_origen=7
        ),
    )
    return await confirmar.confirmar(e.recursos, novela, str(s.solicitud_id))


async def _regenerar_fallando_el_7(e: Entorno) -> tuple[str, Any, str]:
    """Publica la versión 1 y regenera: el 2 se reescribe y se acepta, con un hecho nuevo; el 7
    agota sus intentos. Devuelve también el hash de la versión 1 antes de regenerar."""
    novela = await _publicada(e)
    hash_antes = _hash_v1(e, novela)
    e.modelo.por_defecto["redactor"] = _falla_el(7)
    e.modelo.por_defecto["editor"] = lambda _: corregido(300)
    e.modelo.por_defecto["extractor"] = partial(_extraer, n=102)
    g = await _confirmar(e, novela)
    await e.orquestador().ejecutar(str(g.generacion_id))
    [dirigida] = [
        x for x in await cola.listar_generaciones(e.recursos, novela) if x.tipo == "dirigida"
    ]
    return novela, dirigida, hash_antes


def _hash_v1(e: Entorno, novela: str) -> str:
    [fila] = e.consultar(
        "SELECT hash FROM version_novela WHERE novel_id = ? AND version = 1", novela
    )
    return str(fila["hash"])


def _estados_v1(e: Entorno, novela: str) -> dict[int, str]:
    return {
        f["numero"]: f["estado"]
        for f in e.consultar(
            "SELECT c.numero, c.estado FROM capitulo c JOIN version_capitulo v"
            " ON v.capitulo_id = c.id WHERE v.novel_id = ? AND v.version = 1",
            novela,
        )
    }


@pytest.mark.anyio
async def test_confirmar_no_toca_las_filas_publicadas(entorno: Entorno) -> None:
    """Las marcas de `Obsoleto` nacen en la candidata: filas nuevas de los afectados."""
    novela = await _publicada(entorno)
    await _confirmar(entorno, novela)

    assert set(_estados_v1(entorno, novela).values()) == {"Aceptado"}
    candidata = entorno.consultar(
        "SELECT numero, estado FROM capitulo WHERE novel_id = ? AND version = 2 ORDER BY numero",
        novela,
    )
    assert [(f["numero"], f["estado"]) for f in candidata] == [(2, "Obsoleto"), (7, "Obsoleto")]


@pytest.mark.anyio
async def test_una_regeneracion_que_agota_deja_la_novela_publicada(entorno: Entorno) -> None:
    novela, g, hash_antes = await _regenerar_fallando_el_7(entorno)

    # La generación se detiene; la novela no.
    assert g.estado == "Detenida" and g.detenida_por == "limite-de-intentos-agotado", g
    assert g.version_resultante is None
    [obra] = entorno.consultar("SELECT estado FROM obra WHERE novel_id = ?", novela)
    assert obra["estado"] == "Publicada"
    # La candidata queda rechazada y la vigente sigue siendo la 1.
    versiones = entorno.consultar(
        "SELECT version, estado FROM version_novela WHERE novel_id = ? ORDER BY version", novela
    )
    assert [(v["version"], v["estado"]) for v in versiones] == [(1, "publicada"), (2, "rechazada")]
    assert [v.version for v in await cola_versiones(entorno, novela)] == [1]
    # Y la versión 1 no cambia: ni su hash, ni el estado de sus filas, ni sus hechos.
    assert _hash_v1(entorno, novela) == hash_antes
    assert set(_estados_v1(entorno, novela).values()) == {"Aceptado"}
    v1 = await canon.listar_hechos(entorno.recursos.db, novela, 1)
    assert NALA not in [h.enunciado for h in v1]
    assert not any(DEL_DOS in h.enunciado for h in v1)


async def cola_versiones(e: Entorno, novela: str) -> list[Any]:
    from app.versioning.service import listar_versiones

    return await listar_versiones(e.recursos.db, novela)


@pytest.mark.anyio
async def test_la_siguiente_solicitud_parte_de_la_vigente_y_no_hereda_la_rechazada(
    entorno: Entorno,
) -> None:
    novela, _, _ = await _regenerar_fallando_el_7(entorno)
    entorno.modelo.por_defecto["redactor"] = redactar
    entorno.modelo.por_defecto["extractor"] = partial(_extraer, n=103)

    # El mismo hecho se puede volver a cambiar: en la vigente sigue abierto.
    g = await _confirmar(entorno, novela)
    assert g.capitulos_a_regenerar == [2, 7]
    await entorno.orquestador().ejecutar(str(g.generacion_id))
    [ultima] = [
        x
        for x in await cola.listar_generaciones(entorno.recursos, novela)
        if x.generacion_id == g.generacion_id
    ]
    assert ultima.estado == "Publicada" and ultima.version_resultante == 3, ultima

    [v3] = entorno.consultar(
        "SELECT v.estado, a.version AS anterior FROM version_novela v"
        " JOIN version_novela a ON a.id = v.version_anterior_id"
        " WHERE v.novel_id = ? AND v.version = 3",
        novela,
    )
    assert (v3["estado"], v3["anterior"]) == ("publicada", 1)
    # La 3 lee de la 1 los capítulos no afectados, y ninguna fila de la rechazada.
    filas = entorno.consultar(
        "SELECT vc.numero, c.version FROM version_capitulo vc JOIN capitulo c"
        " ON c.id = vc.capitulo_id WHERE vc.novel_id = ? AND vc.version = 3 ORDER BY vc.numero",
        novela,
    )
    assert {f["numero"]: f["version"] for f in filas} == {
        n: (3 if n in (2, 7) else 1) for n in range(1, 11)
    }
    # Y su canon no hereda nada de la 2: ni su hecho nuevo del capítulo 2 reescrito.
    v3_hechos = [h.enunciado for h in await canon.listar_hechos(entorno.recursos.db, novela, 3)]
    assert NALA in v3_hechos
    assert not any(DEL_DOS in h for h in v3_hechos)
    assert any("En el capítulo 103" in h for h in v3_hechos)
    assert set(_estados_v1(entorno, novela).values()) == {"Aceptado"}
