"""Cierre de F4, real (P44): «el perro se llama Nala» sobre la novela del humo.

Marcado `real`. Trabaja sobre la base de la demo (`STORYMAKER_DB_PATH`) y la novela del humo
(`STORYMAKER_NOVELA_HUMO`): produce su versión 2 con el modelo de verdad. Comprueba lo mismo
que el e2e con dobles —los capítulos no afectados idénticos byte a byte y la versión 1 con su
hash— y deja coste y tokens en `data/humo-regeneracion-<fecha>.json`.
"""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.commons.config import cargar_config
from app.commons.llm import crear_cliente
from app.main import crear_app
from tests.humo.test_novela_real import INFORMES, ClienteMedido, motivo_para_saltar

pytestmark = pytest.mark.real
NUEVO = "El perro se llama Nala"


def test_la_novela_del_humo_cambia_el_nombre_del_perro() -> None:
    cfg = cargar_config()
    motivo = motivo_para_saltar(cfg)
    novela = os.environ.get("STORYMAKER_NOVELA_HUMO")
    if motivo is None and not novela:
        motivo = "sin STORYMAKER_NOVELA_HUMO: no se sabe qué novela regenerar"
    if motivo is not None:
        pytest.skip(motivo)

    cliente = ClienteMedido(crear_cliente(cfg))
    informe: dict[str, Any] = {"fecha": datetime.now(UTC).isoformat(timespec="seconds")}
    ruta = INFORMES / f"humo-regeneracion-{datetime.now(UTC):%Y%m%dT%H%M%S}.json"
    try:
        with TestClient(crear_app(cfg, cliente_modelo=cliente)) as c:
            v1 = c.get(f"/novelas/{novela}/versiones/1").json()
            textos_v1 = {
                x["numero"]: x["texto"]
                for x in c.get(f"/novelas/{novela}/versiones/1/capitulos").json()
            }
            hechos = c.get(f"/novelas/{novela}/versiones/1/hechos").json()
            del_perro = [
                h for h in hechos if "Boya" in h["enunciado"] or "perro" in h["enunciado"].lower()
            ]
            if not del_perro:
                pytest.skip("la novela del humo no tiene un hecho sobre el perro")
            hecho = min(del_perro, key=lambda h: h["capitulo_establece"] or 0)
            s = c.post(
                f"/novelas/{novela}/solicitudes-cambio",
                json={
                    "hecho_id": hecho["hecho_id"],
                    "enunciado_nuevo": NUEVO,
                    "capitulo_origen": 1,
                },
            ).json()
            informe.update(hecho=hecho, analisis=s.get("analisis_impacto"))
            r = c.post(f"/novelas/{novela}/solicitudes-cambio/{s['solicitud_id']}/confirmacion")
            assert r.status_code == 202, r.text
            gid = r.json()["generacion_id"]
            fin = time.monotonic() + cfg.umbrales.coste.latencia_maxima_novela + 60
            while True:
                g: dict[str, Any] = c.get(f"/novelas/{novela}/generaciones/{gid}").json()
                if g["es_terminal"] or time.monotonic() > fin:
                    break
                time.sleep(cfg.umbrales.orquestacion.intervalo_sondeo_segundos)
            informe["generacion"] = g
            assert g["estado"] == "Publicada", g
            afectados = set(s["analisis_impacto"]["capitulos_afectados"])
            textos_v2 = {
                x["numero"]: x["texto"]
                for x in c.get(f"/novelas/{novela}/versiones/2/capitulos").json()
            }
            for n, texto in textos_v1.items():
                if n not in afectados:
                    assert textos_v2[n] == texto, n
            assert c.get(f"/novelas/{novela}/versiones/1").json()["hash"] == v1["hash"]
    finally:
        informe["medidas"] = [m.__dict__ for m in cliente.medidas]
        INFORMES.mkdir(exist_ok=True)
        ruta.write_text(json.dumps(informe, ensure_ascii=False, indent=2, default=str), "utf-8")
        print(f"\ninforme: {ruta}")
