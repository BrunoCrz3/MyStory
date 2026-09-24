"""Humo real: una novela de diez capítulos con el modelo de verdad (plan P26 y P27).

Marcado `real`, fuera de la suite normal (`addopts = -m "not real"`). Cuesta dinero, así que
**se salta con un motivo explícito** si falta la credencial; el P27 trata ese salto como su
condición de parada, no como un verde.

Escribe en la base de `STORYMAKER_DB_PATH`, **no en una temporal**: F4 y F5 reutilizan esa
novela. El tráfico con el proveedor queda en `tests/casetes/` por el grabador, que no
conserva la autenticación.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient

from app.commons.config import cargar_config
from app.commons.llm import ClienteAnthropic
from app.main import crear_app
from tests.arquitectura.comprobadores import RAIZ_REPO
from tests.herramientas.casetes import TransporteGrabador

pytestmark = pytest.mark.real

BRIEF = RAIZ_REPO / "ejemplos" / "brief-ejemplo.json"
CASETE = Path(__file__).resolve().parents[1] / "casetes" / "humo-novela-real.json"


def motivo_para_saltar() -> str | None:
    """Por qué no se puede ejecutar el humo en este entorno, o `None` si se puede."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return (
            "sin ANTHROPIC_API_KEY en el entorno: el humo real no se ejecuta "
            "(en el P27 es la condición de parada 1)"
        )
    if not os.environ.get("STORYMAKER_DB_PATH"):
        return "sin STORYMAKER_DB_PATH: el humo escribe en la base que reutilizan F4 y F5"
    return None


def _esperar_terminal(c: TestClient, novela: str, gid: str, limite_s: float) -> dict[str, Any]:
    intervalo = cargar_config().umbrales.orquestacion.intervalo_sondeo_segundos
    fin = time.monotonic() + limite_s
    while True:
        g: dict[str, Any] = c.get(f"/novelas/{novela}/generaciones/{gid}").json()
        if g["es_terminal"]:
            return g
        if time.monotonic() > fin:
            raise AssertionError(f"la generación no terminó en {limite_s} s: {g}")
        time.sleep(intervalo)


def test_una_novela_real_se_publica_con_diez_capitulos() -> None:
    motivo = motivo_para_saltar()
    if motivo is not None:
        pytest.skip(motivo)

    cfg = cargar_config()
    grabador = TransporteGrabador(httpx2.AsyncHTTPTransport(), CASETE)
    cliente = ClienteAnthropic(cfg, http_client=httpx2.AsyncClient(transport=grabador))
    brief = json.loads(BRIEF.read_text(encoding="utf-8"))

    with TestClient(crear_app(cfg, cliente_modelo=cliente)) as c:
        r = c.post("/novelas", json=brief)
        assert r.status_code == 201, r.text
        novela = r.json()["novel_id"]
        r = c.post(f"/novelas/{novela}/generaciones")
        assert r.status_code == 202, r.text
        gid = r.json()["generacion_id"]
        limite = cfg.umbrales.coste.latencia_maxima_novela + 60
        g = _esperar_terminal(c, novela, gid, limite)
        print(f"\nnovel_id={novela} generacion_id={gid} base={os.environ['STORYMAKER_DB_PATH']}")
        print(f"estado={g['estado']} coste_usd={g['coste_usd']}")

        assert g["estado"] == "Publicada", g
        assert g["version_resultante"] == 1
        capitulos = c.get(f"/novelas/{novela}/versiones/1/capitulos").json()
        assert [x["numero"] for x in capitulos] == list(range(1, 11))
        assert all(x["estado"] == "Aceptado" and x["palabras"] > 0 for x in capitulos)
