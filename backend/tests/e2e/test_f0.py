"""Cierre de F0: `/salud` por HTTP de verdad y arranque que falla en voz alta (spec § 7 F0)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import httpx2
import jsonschema
import yaml

from tests.arquitectura.comprobadores import RAIZ_REPO
from tests.contrato.normalizar import cargar_contrato, schema_de_respuesta
from tests.e2e.proceso import RAIZ_BACKEND, backend, entorno, puerto_libre


def test_salud_por_http_cumple_el_contrato(tmp_path: Path) -> None:
    with backend(entorno(tmp_path / "e2e.db")) as (base, _):
        r = httpx2.get(f"{base}/salud", timeout=5)
    assert r.status_code == 200
    schema = schema_de_respuesta(cargar_contrato(), "obtenerSalud", 200, "application/json")
    assert schema is not None
    jsonschema.validate(r.json(), schema)
    assert r.json()["estado"] == "degradado"


def test_arranque_con_umbral_de_cierre_nulo_falla_nombrando_la_clave(tmp_path: Path) -> None:
    config = tmp_path / "config"
    shutil.copytree(RAIZ_REPO / "config", config)
    umbrales = yaml.safe_load((config / "thresholds.yaml").read_text(encoding="utf-8"))
    umbrales["capitulo"]["longitud_min_palabras"] = None
    (config / "thresholds.yaml").write_text(yaml.safe_dump(umbrales), encoding="utf-8")

    resultado = subprocess.run(
        [sys.executable, "-m", "app", "--sin-env", "--port", str(puerto_libre())],
        cwd=RAIZ_BACKEND,
        env=entorno(tmp_path / "e2e.db", STORYMAKER_CONFIG_DIR=str(config)),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert resultado.returncode != 0
    assert "capitulo.longitud_min_palabras" in resultado.stdout + resultado.stderr
