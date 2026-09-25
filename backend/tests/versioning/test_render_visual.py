"""`render_visual` con Playwright MCP (P47b, RF-QUA-03, CL-02, CL-03, CL-05, TO-026, TO-045).

Dos niveles. `evaluar` es puro: compara lo que la página pinta con lo que la story bible dice de
la versión, y aquí se prueba cada aserción sin navegador. Las pruebas marcadas `mcp` pintan la
página de prueba con el servidor Playwright MCP real (plan § 9); sin él en marcha se saltan
diciendo por qué.
"""

from __future__ import annotations

import os
import socket
from typing import Any
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

from app.commons.config import cargar_config
from app.main import crear_app
from app.versioning import lectura
from app.versioning.render_visual import (
    ASERCIONES,
    Dom,
    LecturaEsperada,
    RenderVisualMCP,
    SinNavegador,
    _errores_consola,
    cardinalidades,
    evaluar,
)
from tests.canon.test_hechos_por_version import publicada_con_uso
from tests.conftest import Instancia
from tests.fixtures.lectura.pagina import datos_de_version, pagina
from tests.fixtures.lectura.servidor import Paginas

MCP_URL = os.environ.get("STORYMAKER_PRUEBAS_MCP_URL", "http://localhost:8931/mcp")


# --- Aserciones puras ------------------------------------------------------------------


def _esperado() -> LecturaEsperada:
    return LecturaEsperada(
        novel_id="n",
        version=2,
        titulo="El verano del Alondra",
        dedicatoria="Para Ondina, que siempre vuelve al puerto.",
        capitulos=[(1, "Uno", False), (2, "Dos", True), (3, "Tres", False)],
        personajes=[("Ondina", [1, 2, 3]), ("Tomás", [2])],
        lugares=[("el puerto", [1, 3])],
    )


def _dom(e: LecturaEsperada) -> dict[str, Any]:
    """El DOM que pintaría una lectura correcta de `e`, con la forma que devuelve la
    extracción."""
    enlaces = sum(len(c) for _, c in e.personajes + e.lugares)
    return {
        "estado": "lista",
        "raiz": {"novel_id": e.novel_id, "version": str(e.version)},
        "cuentas": cardinalidades(e) | {"ficha-enlace-capitulo": enlaces},
        "fuera": [],
        "indice": [
            {"capitulo": str(n), "href": f"#capitulo-{n}", "resuelve": True, "modificado": m}
            for n, _, m in e.capitulos
        ],
        "capitulos": [
            {"capitulo": str(n), "id": f"capitulo-{n}", "titulo": t, "modificado": m}
            for n, t, m in e.capitulos
        ],
        "ficha": [
            {
                "tipo": tipo,
                "nombre": nombre,
                "enlaces": [
                    {"capitulo": str(n), "href": f"#capitulo-{n}", "resuelve": True} for n in caps
                ],
            }
            for tipo, entradas in (("ficha-personaje", e.personajes), ("ficha-lugar", e.lugares))
            for nombre, caps in entradas
        ],
        "portada": {"titulo": e.titulo, "dedicatoria": e.dedicatoria},
        "desbordes": [],
    }


def _hallazgos(dom: dict[str, Any], consola: list[str] | None = None) -> list[str]:
    return [
        f"{h.asercion}:{h.clase}:{h.detalle}"
        for h in evaluar(_esperado(), Dom.model_validate(dom), consola or [])
    ]


def test_cada_asercion_declara_la_tool_que_le_da_la_evidencia() -> None:
    nombres = {a.nombre for a in ASERCIONES}
    assert nombres == {
        "estado",
        "selectores",
        "indice",
        "ficha",
        "portada",
        "consola",
        "desbordes",
        "desplazamiento",
    }
    tools = {"browser_navigate", "browser_evaluate", "browser_console_messages"}
    assert all(a.tools and set(a.tools) <= tools for a in ASERCIONES)


def test_las_cardinalidades_cubren_todo_el_contrato() -> None:
    assert set(cardinalidades(_esperado())) | {"ficha-enlace-capitulo"} == lectura.TESTIDS


def test_una_lectura_correcta_no_tiene_hallazgos() -> None:
    assert _hallazgos(_dom(_esperado())) == []


def test_un_estado_que_no_es_lista_falla_y_no_mira_mas() -> None:
    dom = _dom(_esperado()) | {"estado": "error", "indice": []}
    [h] = _hallazgos(dom)
    assert h.startswith("estado:maquetacion:") and "error" in h


def test_un_selector_ausente_falla_con_su_nombre() -> None:
    dom = _dom(_esperado())
    dom["cuentas"]["portada-dedicatoria"] = 0
    dom["portada"]["dedicatoria"] = None
    hallazgos = _hallazgos(dom)
    assert any(h.startswith("selectores:") and "portada-dedicatoria" in h for h in hallazgos)
    # El dato está en la story bible y no se pinta: bug de maquetación.
    assert any(h.startswith("portada:maquetacion:") for h in hallazgos)


def test_un_selector_fuera_de_su_contenedor_falla() -> None:
    dom = _dom(_esperado()) | {"fuera": ["capitulo-titulo"]}
    assert any("capitulo-titulo" in h for h in _hallazgos(dom) if h.startswith("selectores:"))


def test_un_enlace_roto_del_indice_falla() -> None:
    dom = _dom(_esperado())
    dom["indice"][1] |= {"href": "#capitulo-99", "resuelve": False}
    [h] = _hallazgos(dom)
    assert h.startswith("indice:maquetacion:") and "2" in h


def test_el_indice_fuera_de_orden_o_incompleto_falla() -> None:
    dom = _dom(_esperado())
    dom["indice"] = list(reversed(dom["indice"]))
    assert any(h.startswith("indice:") for h in _hallazgos(dom))


def test_la_marca_de_modificado_tiene_que_ser_exacta() -> None:
    dom = _dom(_esperado())
    dom["capitulos"][0]["modificado"] = True
    assert any(h.startswith("indice:") or "modificado" in h for h in _hallazgos(dom))


def test_un_enlace_de_la_ficha_que_no_lleva_a_su_capitulo_falla() -> None:
    dom = _dom(_esperado())
    dom["ficha"][1]["enlaces"] = [{"capitulo": "3", "href": "#capitulo-3", "resuelve": True}]
    [h] = _hallazgos(dom)
    assert h.startswith("ficha:maquetacion:") and "Tomás" in h


def test_una_entrada_de_ficha_que_falta_falla() -> None:
    dom = _dom(_esperado())
    dom["ficha"] = dom["ficha"][:2]
    assert any(h.startswith("ficha:") and "el puerto" in h for h in _hallazgos(dom))


def test_la_dedicatoria_distinta_falla() -> None:
    dom = _dom(_esperado())
    dom["portada"]["dedicatoria"] = "Otra"
    [h] = _hallazgos(dom)
    assert h.startswith("portada:maquetacion:")


def test_un_dato_que_no_esta_en_la_story_bible_vuelve_a_su_rol_dueno() -> None:
    """O-10, A-80: si el dato falta en la story bible no es maquetación, y el hallazgo nombra
    al rol dueño."""
    e = _esperado().model_copy(
        update={"capitulos": [(1, None, False), (2, "Dos", True), (3, "Tres", False)]}
    )
    dom = _dom(e)
    dom["capitulos"][0]["titulo"] = ""
    [h] = [f"{x.asercion}:{x.clase}:{x.detalle}" for x in evaluar(e, Dom.model_validate(dom), [])]
    assert h.startswith("indice:datos:") and "redactor" in h


def test_errores_de_consola_y_desbordes_fallan() -> None:
    dom = _dom(_esperado()) | {"desbordes": ["capitulo-texto"]}
    hallazgos = _hallazgos(dom, ["[ERROR] TypeError: x is undefined"])
    assert any(h.startswith("consola:maquetacion:") and "TypeError" in h for h in hallazgos)
    assert any(h.startswith("desbordes:maquetacion:") and "capitulo-texto" in h for h in hallazgos)


def test_una_pagina_que_no_se_desplaza_hasta_el_final_falla() -> None:
    """TO-063: el final de la lectura tiene que alcanzarse desplazando la página."""
    dom = _dom(_esperado()) | {"desplazamiento": False}
    hallazgos = _hallazgos(dom, [])
    assert any(h.startswith("desplazamiento:maquetacion:") for h in hallazgos)
    assert not any(h.startswith("desplazamiento") for h in _hallazgos(_dom(_esperado()), []))


# --- Con el servidor Playwright MCP real ------------------------------------------------


def _mcp_en_marcha() -> bool:
    u = urlparse(MCP_URL)
    try:
        with socket.create_connection((u.hostname or "localhost", u.port or 80), timeout=1):
            return True
    except OSError:
        return False


mcp = pytest.mark.skipif(
    not _mcp_en_marcha(),
    reason=f"servidor Playwright MCP no está en marcha en {MCP_URL} (plan § 9)",
)


def _render(instancia: Instancia, paginas: Paginas, espera: float = 5) -> RenderVisualMCP:
    config = cargar_config()
    return RenderVisualMCP(
        config,
        instancia.app.state.recursos.db,
        mcp_url=MCP_URL,
        lectura_url=paginas.base,
        espera_lista_segundos=espera,
    )


@mcp
@pytest.mark.anyio
async def test_una_pagina_correcta_pasa_las_aserciones(
    instancia: Instancia, paginas: Paginas
) -> None:
    novela = publicada_con_uso(instancia)
    paginas.servir(novela, 1, pagina(datos_de_version(instancia.cliente, novela, 1)))
    v = await _render(instancia, paginas)(novel_id=novela, version=1)
    assert v.pasa, v.detalle
    assert v.nombre == "render_visual" and v.valor == 1.0


@mcp
@pytest.mark.anyio
async def test_espera_a_lista_y_error_falla(instancia: Instancia, paginas: Paginas) -> None:
    novela = publicada_con_uso(instancia)
    datos = datos_de_version(instancia.cliente, novela, 1)
    paginas.servir(novela, 1, pagina(datos, estado="error"))
    v = await _render(instancia, paginas)(novel_id=novela, version=1)
    assert not v.pasa and "error" in v.detalle

    paginas.servir(novela, 1, pagina(datos, estado="cargando"))
    v = await _render(instancia, paginas, espera=1)(novel_id=novela, version=1)
    assert not v.pasa and "cargando" in v.detalle


@mcp
@pytest.mark.anyio
async def test_espera_a_que_la_pagina_pase_a_lista(instancia: Instancia, paginas: Paginas) -> None:
    """CL-02: una página que carga la versión después del primer pintado pasa si llega a
    `lista` dentro de la espera."""
    novela = publicada_con_uso(instancia)
    html = pagina(datos_de_version(instancia.cliente, novela, 1), estado="cargando")
    retraso = (
        "<script>setTimeout(() => document.querySelector('main').dataset.estado = 'lista',"
        " 800)</script></body>"
    )
    paginas.servir(novela, 1, html.replace("</body>", retraso))
    v = await _render(instancia, paginas)(novel_id=novela, version=1)
    assert v.pasa, v.detalle


@mcp
@pytest.mark.anyio
async def test_un_selector_ausente_o_un_enlace_roto_fallan_en_el_navegador(
    instancia: Instancia, paginas: Paginas
) -> None:
    novela = publicada_con_uso(instancia)
    datos = datos_de_version(instancia.cliente, novela, 1)
    paginas.servir(novela, 1, pagina(datos, sin=("portada-dedicatoria",)))
    v = await _render(instancia, paginas)(novel_id=novela, version=1)
    assert not v.pasa and "portada-dedicatoria" in v.detalle and "maquetacion" in v.detalle

    roto = pagina(datos).replace('href="#capitulo-3"', 'href="#capitulo-99"', 1)
    paginas.servir(novela, 1, roto)
    v = await _render(instancia, paginas)(novel_id=novela, version=1)
    assert not v.pasa and "indice" in v.detalle


@mcp
@pytest.mark.anyio
async def test_un_error_de_consola_falla(instancia: Instancia, paginas: Paginas) -> None:
    novela = publicada_con_uso(instancia)
    html = pagina(datos_de_version(instancia.cliente, novela, 1))
    paginas.servir(novela, 1, html.replace("</body>", "<script>null.x()</script></body>"))
    v = await _render(instancia, paginas)(novel_id=novela, version=1)
    assert not v.pasa and "consola" in v.detalle


@pytest.mark.anyio
async def test_sin_servidor_mcp_falla_con_el_motivo(instancia: Instancia) -> None:
    novela = publicada_con_uso(instancia)
    render = RenderVisualMCP(
        cargar_config(),
        instancia.app.state.recursos.db,
        mcp_url="http://localhost:9/mcp",
        lectura_url="http://127.0.0.1:9",
    )
    v = await render(novel_id=novela, version=1)
    assert not v.pasa and "servidor Playwright MCP" in v.detalle


def test_produccion_elige_el_render_segun_el_entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    """A-114: sin las dos variables, `SinNavegador`; con ellas, el cliente MCP."""
    with TestClient(crear_app()) as c:
        render = c.app.state.worker.orquestador.publicador.render  # type: ignore[attr-defined]
        assert isinstance(render, SinNavegador)
    monkeypatch.setenv("PLAYWRIGHT_MCP_URL", MCP_URL)
    monkeypatch.setenv("STORYMAKER_LECTURA_URL", "http://127.0.0.1:5173")
    with TestClient(crear_app()) as c:
        render = c.app.state.worker.orquestador.publicador.render  # type: ignore[attr-defined]
        assert isinstance(render, RenderVisualMCP)
        assert render.lectura_url == "http://127.0.0.1:5173"


def test_los_errores_de_consola_se_leen_tras_la_cabecera() -> None:
    """A-118: la cabecera puede tener una o dos líneas; una excepción no capturada sale
    sin prefijo. Todo error cuenta, también un 404 del favicon: A-124 se retiró al servir el
    frontend su favicon."""
    salto = chr(10)
    solo_errores = salto.join(
        [
            "### Result",
            "Total messages: 1 (Errors: 1, Warnings: 0)",
            "",
            "TypeError: Cannot read properties of null (reading 'x')",
            "    at http://127.0.0.1:1/:1:102",
        ]
    )
    assert _errores_consola(solo_errores) == [
        "TypeError: Cannot read properties of null (reading 'x')"
    ]
    con_avisos = salto.join(
        [
            "### Result",
            "Total messages: 6 (Errors: 2, Warnings: 2)",
            'Returning 2 messages for level "error"',
            "",
            "[ERROR] Failed to load resource: the server responded with a status of 404 (Not Found)"
            " @ http://127.0.0.1:5173/favicon.ico:0",
            "[ERROR] Uncaught ReferenceError: x is not defined",
        ]
    )
    assert _errores_consola(con_avisos) == [
        "[ERROR] Failed to load resource: the server responded with a status of 404 (Not Found)"
        " @ http://127.0.0.1:5173/favicon.ico:0",
        "[ERROR] Uncaught ReferenceError: x is not defined",
    ]
    sin_errores = salto.join(["### Result", "Total messages: 3 (Errors: 0, Warnings: 3)"])
    assert _errores_consola(sin_errores) == []


@mcp
@pytest.mark.anyio
async def test_una_pagina_con_el_desplazamiento_bloqueado_falla(
    instancia: Instancia, paginas: Paginas
) -> None:
    """TO-063: una altura de pantalla con `overflow: hidden` deja el final fuera de alcance."""
    novela = publicada_con_uso(instancia)
    bloqueo = (
        "<style>html, body { height: 100%; overflow: hidden; }"
        " main { padding-bottom: 4000px; }</style></head>"
    )
    html = pagina(datos_de_version(instancia.cliente, novela, 1)).replace("</head>", bloqueo, 1)
    paginas.servir(novela, 1, html)
    v = await _render(instancia, paginas)(novel_id=novela, version=1)
    assert not v.pasa and "desplazamiento" in v.detalle
