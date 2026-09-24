"""Ciclo de un capítulo: redactor, hook de policy, hook de capítulo y decisión
(RF-QUA-01, RF-QUA-02 parcial, RF-GUARD-03, RF-NOVEL-04 parcial, RF-OBS-03)."""

from __future__ import annotations

import pytest

from app.process.capitulo import ciclo_capitulo
from tests.conftest import Entorno
from tests.fixtures.borradores import borrador
from tests.fixtures.planificada import novela_planificada

LIMITE = 3


def _estado(entorno: Entorno, novela: str, numero: int = 1) -> tuple[str, int]:
    fila = entorno.consultar(
        "SELECT estado, intentos FROM capitulo WHERE novel_id = ? AND numero = ?", novela, numero
    )[0]
    return fila["estado"], fila["intentos"]


@pytest.mark.anyio
async def test_un_borrador_valido_queda_listo_para_aceptar(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    entorno.modelo.encolar("redactor", borrador())
    r = await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=1)
    assert r.accion == "aceptar"
    assert r.borrador is not None and r.borrador.titulo == "La primera travesía"
    assert _estado(entorno, novela) == ("Validando", 0)
    nombres = [s.nombre for s in entorno.trazas.scores]
    assert nombres == ["schema_valido", "palabras_prohibidas", "longitud", "nombres_exactos"]
    assert all(s.valor == 1.0 for s in entorno.trazas.scores)
    assert entorno.trazas.nombres("generacion")[-1] == "writer"


@pytest.mark.anyio
async def test_capitulo_corto_vuelve_al_redactor_con_el_informe(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    entorno.modelo.encolar("redactor", borrador(500), borrador())
    r = await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=1)
    assert r.accion == "aceptar"
    assert _estado(entorno, novela) == ("Validando", 1)
    segunda = entorno.modelo.peticiones[-1].mensajes[0].contenido
    assert "500 palabras" in segunda


@pytest.mark.anyio
async def test_nombre_mal_escrito_vuelve_al_redactor(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    malo = borrador(extra="Aquella tarde su hermana llamó a Martha desde el muelle.")
    entorno.modelo.encolar("redactor", malo, borrador())
    r = await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=1)
    assert r.accion == "aceptar"
    assert [s.valor for s in entorno.trazas.scores_de("nombres_exactos")] == [0.0, 1.0]


@pytest.mark.anyio
async def test_palabra_vetada_se_registra_y_el_hook_de_capitulo_no_corre(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    malo = borrador(extra="Luis la esperaba en el puerto aquella tarde de viento.")
    entorno.modelo.encolar("redactor", malo, borrador())
    await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=1)
    assert [s.valor for s in entorno.trazas.scores_de("palabras_prohibidas")] == [0.0, 1.0]
    assert len(entorno.trazas.scores_de("longitud")) == 1  # solo en el intento limpio
    coincidencia = entorno.consultar("SELECT palabra, nivel, intento FROM coincidencia")
    assert [tuple(c) for c in coincidencia] == [("Luis", "novela", 0)]
    reglas = [f["regla"] for f in entorno.consultar("SELECT regla FROM audit_log ORDER BY rowid")]
    assert "palabra-prohibida" in reglas


@pytest.mark.anyio
async def test_dos_pasadas_con_palabra_vetada_detienen_sin_tercer_intento(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    malo = borrador(extra="Luis la esperaba en el puerto aquella tarde de viento.")
    entorno.modelo.encolar("redactor", malo, malo, borrador())
    r = await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=1)
    assert r.accion == "detener"
    assert r.detenida_por == "palabra-prohibida-persistente"
    assert entorno.modelo.llamadas["redactor"] == 2
    assert _estado(entorno, novela)[0] == "Agotado"


@pytest.mark.anyio
async def test_agotar_los_intentos(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    entorno.modelo.encolar("redactor", *[borrador(300)] * (LIMITE + 1))
    r = await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=1)
    assert r.accion == "agotar"
    assert r.detenida_por == "limite-de-intentos-agotado"
    assert entorno.modelo.llamadas["redactor"] == LIMITE + 1
    assert _estado(entorno, novela) == ("Agotado", LIMITE)


@pytest.mark.anyio
async def test_salida_del_redactor_sin_schema_falla_schema_valido(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    entorno.modelo.encolar("redactor", {"titulo": "Sin texto"}, borrador())
    r = await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=1)
    assert r.accion == "aceptar"
    assert [s.valor for s in entorno.trazas.scores_de("schema_valido")][-2:] == [0.0, 1.0]


@pytest.mark.anyio
async def test_el_contexto_del_redactor_lleva_su_brief_de_capitulo(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    entorno.modelo.encolar("redactor", borrador())
    await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=1)
    peticion = entorno.modelo.peticiones[-1]
    usuario = peticion.mensajes[0].contenido
    estructural = usuario.split('<capa nombre="estructural">', 1)[1].split("</capa>", 1)[0]
    assert "está más cerca del mar" in estructural
    anticontexto = usuario.split('<capa nombre="anticontexto">', 1)[1].split("</capa>", 1)[0]
    assert "Luis" in anticontexto
    assert peticion.esquema_salida is not None
    consumo = entorno.consultar(
        "SELECT tokens_entrada, coste_usd FROM capitulo WHERE novel_id = ? AND numero = 1", novela
    )[0]
    assert consumo["tokens_entrada"] > 0 and consumo["coste_usd"] > 0
