"""Sesión, traza, span y score; y el único camino al modelo (RF-OBS-01…04, RNF-08)."""

from __future__ import annotations

import logging

import pytest

from app.commons.config import Rol, cargar_config
from app.commons.llm import Mensaje, Peticion
from app.commons.llm.llamar import ContextoNoCabe, LlamadorModelo
from app.commons.llm.pool import PoolEnVuelo
from app.commons.observabilidad import (
    AGENTE_DE_ROL,
    NOMBRES_SPAN,
    TrazadorLangfuse,
    validar_nombre_span,
)
from tests.arquitectura.comprobadores import RAIZ_REPO
from tests.dobles.modelo import ModeloGuionizado
from tests.dobles.trazador import RegistroTrazas

CONFIG = cargar_config(RAIZ_REPO / "config")


def _peticion(rol: Rol = "redactor", contenido: str = "Escribe.") -> Peticion:
    return Peticion(
        rol=rol,
        system="sistema",
        mensajes=[Mensaje(role="user", contenido=contenido)],
        prompt="writer",
        hash_prompt="deadbeef",
    )


@pytest.mark.anyio
async def test_cada_llamada_deja_un_span_del_rol_con_tokens_coste_y_hash() -> None:
    doble = ModeloGuionizado(
        CONFIG,
        por_defecto={
            "redactor": lambda p: "texto",
            "planificador": lambda p: "plan",
            "judge": lambda p: "nota",
        },
    )
    trazas = RegistroTrazas()
    llamador = LlamadorModelo(CONFIG, doble, PoolEnVuelo(CONFIG.umbrales.en_vuelo.total), trazas)
    with trazas.traza("generacion", novel_id="n1"):
        roles: tuple[Rol, ...] = ("redactor", "planificador", "judge")
        for rol in roles:
            await llamador.llamar(_peticion(rol))

    generaciones = [s for s in trazas.spans if s.tipo == "generacion"]
    assert [g.nombre for g in generaciones] == ["writer", "planner", "judge"]
    for g in generaciones:
        assert g.metadata["hash_prompt"] == "deadbeef"
        assert g.tokens_entrada and g.tokens_salida
        assert g.coste_usd is not None and g.latencia_s is not None
        assert g.sesion == "n1"
    assert len(generaciones) == doble.llamadas["redactor"] + doble.llamadas["planificador"] + 1


@pytest.mark.anyio
async def test_un_ensamblado_que_no_cabe_falla_sin_llamar() -> None:
    doble = ModeloGuionizado(CONFIG, por_defecto={"redactor": lambda p: "texto"})
    llamador = LlamadorModelo(CONFIG, doble, PoolEnVuelo(10**9), RegistroTrazas())
    enorme = "x" * (CONFIG.umbrales.contexto.total * 4 + 4)
    with pytest.raises(ContextoNoCabe):
        await llamador.llamar(_peticion(contenido=enorme))
    assert doble.llamadas["redactor"] == 0


@pytest.mark.anyio
async def test_la_llamada_pasa_por_el_pool() -> None:
    pool = PoolEnVuelo(CONFIG.umbrales.en_vuelo.total)
    vistos: list[int] = []

    def mirar(p: Peticion) -> str:
        vistos.append(pool.ocupado)
        return "texto"

    llamador = LlamadorModelo(
        CONFIG, ModeloGuionizado(CONFIG, por_defecto={"redactor": mirar}), pool, RegistroTrazas()
    )
    await llamador.llamar(_peticion())
    assert vistos[0] > 0
    assert pool.ocupado == 0


def test_los_nombres_de_span_son_los_de_architecture() -> None:
    assert set(AGENTE_DE_ROL.values()) == {
        "interviewer",
        "planner",
        "writer",
        "judge",
        "editor",
        "extractor",
    }
    assert {"consultar_story_bible", "extraer_hechos_texto_libre", "detectar_contradiccion"} <= (
        NOMBRES_SPAN
    )
    with pytest.raises(ValueError, match="inventado"):
        validar_nombre_span("inventado")


def test_sin_credenciales_el_trazador_queda_degradado_y_no_lanza(
    caplog: pytest.LogCaptureFixture,
) -> None:
    trazador = TrazadorLangfuse()
    assert trazador.degradado
    caplog.set_level(logging.INFO, logger="storymaker.trazas")
    with trazador.traza("generacion", novel_id="n1") as t:
        with trazador.span("consultar_story_bible", entrada={"q": 1}):
            pass
        trazador.score("longitud", 1.0, comentario=None)
        assert t.traza_id is None
        assert t.id_local
    assert any("consultar_story_bible" in r.getMessage() for r in caplog.records)
    with pytest.raises(ValueError), trazador.span("inventado"):
        pass
    trazador.cerrar()
