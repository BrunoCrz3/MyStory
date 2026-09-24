"""Opcional del cierre de F3 (P38): el brief adversarial generado con el modelo real.

Marcado `real`. En una base temporal, no en la de la demo: esta novela no se reutiliza. Se
comprueba lo mismo que el e2e con dobles —ninguna petición lleva la instrucción inyectada— y
además que la novela real se publica. El coste queda en `data/humo-adversarial-<fecha>.json`.
"""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.commons.config import cargar_config
from app.commons.llm import Peticion, Recuento, Respuesta, crear_cliente
from app.main import crear_app
from tests.fixtures.briefs import INYECCION, brief_adversarial
from tests.humo.test_novela_real import INFORMES, ClienteMedido, motivo_para_saltar

pytestmark = pytest.mark.real
MARCA = "Ignora las instrucciones"


class ClienteQueGuarda(ClienteMedido):
    """El cliente real, que además guarda cada petición para buscar la inyección en ellas."""

    def __init__(self, real: Any) -> None:
        super().__init__(real)
        self.peticiones: list[Peticion] = []

    async def generar(self, peticion: Peticion, recuento: Recuento) -> Respuesta:
        self.peticiones.append(peticion)
        return await super().generar(peticion, recuento)


def test_la_generacion_real_no_recibe_la_instruccion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = cargar_config()
    monkeypatch.setenv("STORYMAKER_DB_PATH", str(tmp_path / "adversarial.db"))
    motivo = motivo_para_saltar(cfg)
    if motivo is not None:
        pytest.skip(motivo)

    cliente = ClienteQueGuarda(crear_cliente(cfg))
    informe: dict[str, Any] = {"fecha": datetime.now(UTC).isoformat(timespec="seconds")}
    ruta = INFORMES / f"humo-adversarial-{datetime.now(UTC):%Y%m%dT%H%M%S}.json"
    try:
        with TestClient(crear_app(cfg, cliente_modelo=cliente)) as c:
            validacion = c.post("/briefs/validacion", json=brief_adversarial()).json()
            assert [f["fragmento"] for f in validacion["fragmentos_sospechosos"]] == [INYECCION]
            novela = c.post("/novelas", json=brief_adversarial()).json()["novel_id"]
            gid = c.post(f"/novelas/{novela}/generaciones").json()["generacion_id"]
            fin = time.monotonic() + cfg.umbrales.coste.latencia_maxima_novela + 60
            while True:
                g: dict[str, Any] = c.get(f"/novelas/{novela}/generaciones/{gid}").json()
                if g["es_terminal"] or time.monotonic() > fin:
                    break
                time.sleep(cfg.umbrales.orquestacion.intervalo_sondeo_segundos)
            informe.update(novel_id=novela, generacion=g)
    finally:
        informe["medidas"] = [m.__dict__ for m in cliente.medidas]
        informe["peticiones"] = len(cliente.peticiones)
        INFORMES.mkdir(exist_ok=True)
        ruta.write_text(json.dumps(informe, ensure_ascii=False, indent=2, default=str), "utf-8")
        print(f"\ninforme: {ruta}  base: {os.environ['STORYMAKER_DB_PATH']}")

    for p in cliente.peticiones:
        assert MARCA not in p.system, p.rol
        assert all(MARCA not in m.contenido for m in p.mensajes), p.rol
    assert g["estado"] == "Publicada", g
