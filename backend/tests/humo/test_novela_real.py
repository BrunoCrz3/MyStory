"""Humo real: una novela de diez capítulos con el modelo de verdad (plan P26 y P27).

Marcado `real`, fuera de la suite normal (`addopts = -m "not real"`). Cuesta dinero, así que
**se salta con un motivo explícito** si falta lo que el proveedor configurado necesita: la
clave con `proveedor: api`, el CLI con `proveedor: claude_code` (I-04). El P27 trata ese
salto como su condición de parada, no como un verde.

Escribe en la base de `STORYMAKER_DB_PATH`, **no en una temporal**: F4 y F5 reutilizan esa
novela. Con `proveedor: api` el tráfico queda en `tests/casetes/` por el grabador, que no
conserva la autenticación. Con los dos, cada llamada deja sus tokens —entrada estimada y
real, salida y razonamiento— en `data/humo-<fecha>.json` (I-02).
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient

from app.commons.config import Config, cargar_config
from app.commons.llm import (
    ClienteAnthropic,
    ClienteModelo,
    ErrorModelo,
    Peticion,
    Recuento,
    Respuesta,
    crear_cliente,
)
from app.commons.llm.claude_code import resolver_ejecutable
from app.main import crear_app
from tests.arquitectura.comprobadores import RAIZ_REPO
from tests.herramientas.casetes import TransporteGrabador

pytestmark = pytest.mark.real

BRIEF = RAIZ_REPO / "ejemplos" / "brief-ejemplo.json"
CASETE = Path(__file__).resolve().parents[1] / "casetes" / "humo-novela-real.json"
INFORMES = RAIZ_REPO / "data"


def motivo_para_saltar(config: Config) -> str | None:
    """Por qué no se puede ejecutar el humo en este entorno, o `None` si se puede."""
    if config.modelos.proveedor == "api" and not os.environ.get("ANTHROPIC_API_KEY"):
        return (
            "proveedor api sin ANTHROPIC_API_KEY en el entorno: el humo real no se ejecuta "
            "(en el P27 es la condición de parada 1)"
        )
    if config.modelos.proveedor == "claude_code":
        try:
            resolver_ejecutable(os.environ)
        except ErrorModelo as e:
            return f"proveedor claude_code sin CLI: {e}"
    if not os.environ.get("STORYMAKER_DB_PATH"):
        return "sin STORYMAKER_DB_PATH: el humo escribe en la base que reutilizan F4 y F5"
    return None


@dataclass
class Medida:
    rol: str
    capitulo: int | None
    estimados_entrada: int
    tokens_entrada: int
    tokens_salida: int
    tokens_razonamiento: int | None
    max_tokens: int
    coste_usd: float
    latencia_s: float


class ClienteMedido:
    """El cliente real, más una anotación por llamada. No sustituye nada: delega en él."""

    def __init__(self, real: ClienteModelo) -> None:
        self.real = real
        self.medidas: list[Medida] = []

    async def contar_tokens(self, peticion: Peticion) -> Recuento:
        return await self.real.contar_tokens(peticion)

    async def generar(self, peticion: Peticion, recuento: Recuento) -> Respuesta:
        respuesta = await self.real.generar(peticion, recuento)
        m = re.search(r"Escribe el capítulo (\d+)", peticion.mensajes[0].contenido)
        self.medidas.append(
            Medida(
                rol=peticion.rol,
                capitulo=int(m.group(1)) if m else None,
                estimados_entrada=recuento.tokens_entrada,
                tokens_entrada=respuesta.tokens_entrada,
                tokens_salida=respuesta.tokens_salida,
                tokens_razonamiento=respuesta.tokens_razonamiento,
                max_tokens=recuento.max_tokens,
                coste_usd=respuesta.coste_usd,
                latencia_s=round(respuesta.latencia_s, 1),
            )
        )
        return respuesta


def _cliente(cfg: Config) -> ClienteModelo:
    if cfg.modelos.proveedor == "api":
        grabador = TransporteGrabador(httpx2.AsyncHTTPTransport(), CASETE)
        return ClienteAnthropic(cfg, http_client=httpx2.AsyncClient(transport=grabador))
    return crear_cliente(cfg)


def _esperar_terminal(
    c: TestClient, novela: str, gid: str, limite_s: float, intervalo: float
) -> dict[str, Any]:
    fin = time.monotonic() + limite_s
    while True:
        g: dict[str, Any] = c.get(f"/novelas/{novela}/generaciones/{gid}").json()
        if g["es_terminal"]:
            return g
        if time.monotonic() > fin:
            raise AssertionError(f"la generación no terminó en {limite_s} s: {g}")
        time.sleep(intervalo)


def _url_traza(traza: str | None) -> str | None:
    if not traza:
        return None
    try:
        from langfuse import get_client

        url: str | None = get_client().get_trace_url(trace_id=traza)
        return url
    except Exception:  # la URL es un extra del informe, no parte de la prueba
        return None


def test_una_novela_real_se_publica_con_diez_capitulos() -> None:
    cfg = cargar_config()
    motivo = motivo_para_saltar(cfg)
    if motivo is not None:
        pytest.skip(motivo)

    cliente = ClienteMedido(_cliente(cfg))
    brief = json.loads(BRIEF.read_text(encoding="utf-8"))
    informe: dict[str, Any] = {
        "fecha": datetime.now(UTC).isoformat(timespec="seconds"),
        "proveedor": cfg.modelos.proveedor,
        "base": os.environ["STORYMAKER_DB_PATH"],
    }
    ruta_informe = INFORMES / f"humo-{datetime.now(UTC):%Y%m%dT%H%M%S}.json"
    capitulos: list[dict[str, Any]] = []

    try:
        with TestClient(crear_app(cfg, cliente_modelo=cliente)) as c:
            r = c.post("/novelas", json=brief)
            assert r.status_code == 201, r.text
            novela = r.json()["novel_id"]
            r = c.post(f"/novelas/{novela}/generaciones")
            assert r.status_code == 202, r.text
            gid = r.json()["generacion_id"]
            informe.update(novel_id=novela, generacion_id=gid)
            g = _esperar_terminal(
                c,
                novela,
                gid,
                cfg.umbrales.coste.latencia_maxima_novela + 60,
                cfg.umbrales.orquestacion.intervalo_sondeo_segundos,
            )
            informe["generacion"] = g
            informe["url_traza"] = _url_traza(g.get("traza_langfuse_id"))
            if g["estado"] == "Publicada":
                capitulos = c.get(f"/novelas/{novela}/versiones/1/capitulos").json()
    finally:
        informe["medidas"] = [asdict(m) for m in cliente.medidas]
        INFORMES.mkdir(exist_ok=True)
        ruta_informe.write_text(json.dumps(informe, ensure_ascii=False, indent=2), "utf-8")
        print(f"\ninforme: {ruta_informe}")

    assert g["estado"] == "Publicada", g
    assert g["version_resultante"] == 1
    assert [x["numero"] for x in capitulos] == list(range(1, 11))
    assert all(x["estado"] == "Aceptado" and x["palabras"] > 0 for x in capitulos)
