"""Confirmación de una solicitud: retcon, obsolescencia y regeneración dirigida encolada
(RF-VER-08 mitad canon, RF-CANON-05 parcial)."""

from __future__ import annotations

import uuid
from functools import partial

import pytest

from app.canon import service as canon
from app.commons.errores import HechoNoEncontrado
from app.process import cola
from app.versioning import confirmar, solicitud
from app.versioning.schemas import NuevaSolicitudCambio
from tests.canon.test_hechos_por_version import _extraer, publicada_con_uso
from tests.conftest import Entorno, Instancia, ValidarContrato
from tests.dobles.guiones import guion_completo
from tests.fixtures.briefs import brief_ejemplo


async def _publicada(e: Entorno) -> str:
    """La novela del P39 (el capítulo 7 usa el hecho del 2), generada sin worker."""
    guion_completo(e.modelo)
    guiones = [partial(_extraer, n=n) for n in range(1, 11)]
    guiones[6] = partial(_extraer, n=7, usados=["H2"])
    e.modelo.encolar("extractor", *guiones)
    novela = await e.crear_novela(brief_ejemplo())
    g = await cola.lanzar_generacion(e.recursos, novela)
    await e.orquestador().ejecutar(str(g.generacion_id))
    return novela


async def _solicitud(e: Entorno, novela: str) -> tuple[str, canon.Hecho]:
    hechos = await e.recursos.db.ejecutar(
        lambda con: canon.hechos_vigentes(con, novel_id=novela, version=1)
    )
    del_dos = next(h for h in hechos if h.capitulo_establece == 2)
    s = await solicitud.crear_solicitud(
        e.recursos.db,
        e.recursos.config,
        novela,
        NuevaSolicitudCambio(
            hecho_id=uuid.UUID(del_dos.hecho_id),
            enunciado_nuevo="El perro se llama Nala",
            capitulo_origen=7,
        ),
    )
    return str(s.solicitud_id), del_dos


@pytest.mark.anyio
async def test_confirmar_aplica_el_retcon_marca_obsoletos_y_encola_la_dirigida(
    entorno: Entorno,
) -> None:
    novela = await _publicada(entorno)
    sid, viejo = await _solicitud(entorno, novela)

    g = await confirmar.confirmar(entorno.recursos, novela, sid)
    assert g.tipo == "dirigida" and g.capitulos_a_regenerar == [2, 7]

    [fila] = entorno.consultar(
        "SELECT estado, version_desde, version_hasta FROM hecho WHERE id = ?", viejo.hecho_id
    )
    assert (fila["estado"], fila["version_desde"], fila["version_hasta"]) == ("retconeado", 1, 2)
    [nuevo] = entorno.consultar(
        "SELECT id, estado, version_desde, version_hasta FROM hecho"
        " WHERE novel_id = ? AND enunciado = 'El perro se llama Nala'",
        novela,
    )
    assert (nuevo["estado"], nuevo["version_desde"], nuevo["version_hasta"]) == (
        "adoptado",
        2,
        None,
    )
    [retcon] = entorno.consultar("SELECT * FROM retcon WHERE solicitud_id = ?", sid)
    assert retcon["hecho_viejo_id"] == viejo.hecho_id and retcon["hecho_nuevo_id"] == nuevo["id"]
    assert retcon["version"] == 2

    estados = {
        f["numero"]: f["estado"]
        for f in entorno.consultar(
            "SELECT c.numero, c.estado FROM capitulo c JOIN version_capitulo v"
            " ON v.capitulo_id = c.id WHERE v.novel_id = ? AND v.version = 1",
            novela,
        )
    }
    assert {n for n, e in estados.items() if e == "Obsoleto"} == {2, 7}
    assert all(e == "Aceptado" for n, e in estados.items() if n not in (2, 7))

    [trabajo] = entorno.consultar(
        "SELECT tipo, estado_cola, version_objetivo, capitulos_a_regenerar, solicitud_id"
        " FROM trabajo WHERE novel_id = ? AND tipo = 'dirigida'",
        novela,
    )
    assert trabajo["estado_cola"] == "pendiente" and trabajo["version_objetivo"] == 2
    assert trabajo["capitulos_a_regenerar"] == "[2, 7]" and trabajo["solicitud_id"] == sid
    [s] = entorno.consultar("SELECT estado FROM solicitud_cambio WHERE id = ?", sid)
    assert s["estado"] == "confirmada"

    # La versión 1 sigue devolviendo el hecho viejo; la 2 verá el nuevo.
    v1 = await canon.listar_hechos(entorno.recursos.db, novela, 1)
    assert viejo.enunciado in [h.enunciado for h in v1]
    assert "El perro se llama Nala" not in [h.enunciado for h in v1]


@pytest.mark.anyio
async def test_una_solicitud_sin_hecho_no_se_puede_confirmar(entorno: Entorno) -> None:
    novela = await _publicada(entorno)
    s = await solicitud.crear_solicitud(
        entorno.recursos.db,
        entorno.recursos.config,
        novela,
        NuevaSolicitudCambio(
            fragmento="Nada de esto sostiene ningún hecho.", enunciado_nuevo="x", capitulo_origen=3
        ),
    )
    with pytest.raises(HechoNoEncontrado):
        await confirmar.confirmar(entorno.recursos, novela, str(s.solicitud_id))


def test_confirmar_por_http_responde_202_y_no_se_confirma_dos_veces(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    novela = publicada_con_uso(instancia)
    hechos = instancia.cliente.get(f"/novelas/{novela}/versiones/1/hechos").json()
    del_dos = next(h for h in hechos if h["capitulo_establece"] == 2)
    s = instancia.cliente.post(
        f"/novelas/{novela}/solicitudes-cambio",
        json={"hecho_id": del_dos["hecho_id"], "enunciado_nuevo": "Nala", "capitulo_origen": 2},
    ).json()
    ruta = f"/novelas/{novela}/solicitudes-cambio/{s['solicitud_id']}/confirmacion"

    r = instancia.cliente.post(ruta)
    validar_contra_contrato(r, "confirmarSolicitudCambio")
    assert r.status_code == 202, r.text
    g = r.json()
    assert g["tipo"] == "dirigida" and g["capitulos_a_regenerar"] == [2, 7]
    assert r.headers["location"] == f"/novelas/{novela}/generaciones/{g['generacion_id']}"

    r = instancia.cliente.post(ruta)
    validar_contra_contrato(r, "confirmarSolicitudCambio")
    assert r.status_code == 409
    assert r.json()["type"] in ("/problemas/transicion-invalida", "/problemas/generacion-en-curso")
