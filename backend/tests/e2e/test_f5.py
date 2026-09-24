"""Cierre de F5: de la generación al PDF, con `render_visual` real (P49).

El backend corre como proceso real con los dobles del modelo, pero con el `render_visual` de
producción: el gate pinta la versión **candidata** con el servidor Playwright MCP sobre una
página de lectura que, como la del frontend, lee la versión de la API al pedirla. Si pasa, la
versión se publica; entonces la ficha y la portada se leen por HTTP y el export sale con su
paridad. Sin el servidor MCP o sin el Chromium de Playwright se salta diciendo por qué.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import httpx2
import pytest

from app.versioning import export
from tests.contrato.pendientes import PENDIENTES
from tests.e2e.proceso import backend, entorno
from tests.fixtures.briefs import brief_ejemplo
from tests.fixtures.lectura.pagina import datos_de_version, pagina
from tests.fixtures.lectura.servidor import Paginas
from tests.versioning.test_render_visual import MCP_URL, mcp

APP_CON_DOBLES = ["-m", "tests.e2e.app_con_dobles"]


def _hasta(leer: Any, condicion: Any, limite: float = 120) -> Any:
    fin = time.monotonic() + limite
    valor = leer()
    while not condicion(valor):
        if time.monotonic() > fin:
            raise AssertionError(f"no se llegó a la condición: {valor}")
        time.sleep(0.2)
        valor = leer()
    return valor


def test_conformidad_completa() -> None:
    """El P49 exige que no quede ninguna operación del contrato sin implementar."""
    assert frozenset() == PENDIENTES


@mcp
@pytest.mark.skipif(
    not export.navegador_instalado(),
    reason="falta el Chromium de Playwright: uv run playwright install chromium (plan § 9)",
)
def test_de_la_generacion_al_pdf_con_render_visual_real(tmp_path: Path, paginas: Paginas) -> None:
    env = entorno(
        tmp_path / "f5.db",
        PLAYWRIGHT_MCP_URL=MCP_URL,
        STORYMAKER_LECTURA_URL=paginas.base,
        STORYMAKER_E2E_RENDER="real",
    )
    with (
        backend(env, modulo=APP_CON_DOBLES) as (base, _),
        httpx2.Client(base_url=base, timeout=30) as c,
    ):
        paginas.generador = lambda novela, version: pagina(datos_de_version(c, novela, version))

        novela = c.post("/novelas", json=brief_ejemplo()).json()["novel_id"]
        gid = c.post(f"/novelas/{novela}/generaciones").json()["generacion_id"]
        g = _hasta(
            lambda: c.get(f"/novelas/{novela}/generaciones/{gid}").json(),
            lambda g: g["es_terminal"],
        )
        # Publicada solo si `render_visual` pintó la candidata y pasó (RNF-19).
        assert g["estado"] == "Publicada", g
        v = c.get(f"/novelas/{novela}/versiones/1").json()
        assert v["estado"] == "publicada"
        assert c.get(f"/novelas/{novela}").json()["version_vigente"] == 1

        ficha = c.get(f"/novelas/{novela}/versiones/1/ficha").json()
        assert any(p["nombre"] == "Marta" and p["capitulos"] for p in ficha["personajes"])
        portada = c.get(f"/novelas/{novela}/versiones/1/portada").json()
        assert portada["dedicatoria"] == brief_ejemplo()["dedicatoria"]

        ruta = f"/novelas/{novela}/versiones/1/export"
        assert c.post(ruta).status_code == 202
        exportado = _hasta(lambda: c.post(ruta).json(), lambda e: e["estado"] != "en-curso")
        assert exportado["estado"] == "disponible", exportado
        assert exportado["paridad_pdf_web"] is True
        r = c.get(ruta)
        assert r.status_code == 200 and r.content.startswith(b"%PDF")
