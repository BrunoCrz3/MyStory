"""Carga y validación de `config/` con fallo en voz alta (RNF-14, RNF-15, RF-CTX-05)."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from app.commons.config import ConfigInvalida, cargar_config
from app.main import crear_app
from tests.arquitectura.comprobadores import RAIZ_REPO

CONFIG_REAL = RAIZ_REPO / "config"

Mutador = Callable[[dict[str, Any], dict[str, Any]], None]


@pytest.fixture
def config_con(tmp_path: Path) -> Callable[[Mutador], Path]:
    """Copia `config/` a `tmp_path`, aplica una mutación y devuelve la carpeta."""

    def preparar(mutar: Mutador) -> Path:
        destino = tmp_path / "config"
        shutil.copytree(CONFIG_REAL, destino)
        umbrales = yaml.safe_load((destino / "thresholds.yaml").read_text(encoding="utf-8"))
        modelos = yaml.safe_load((destino / "models.yaml").read_text(encoding="utf-8"))
        mutar(umbrales, modelos)
        (destino / "thresholds.yaml").write_text(yaml.safe_dump(umbrales), encoding="utf-8")
        (destino / "models.yaml").write_text(yaml.safe_dump(modelos), encoding="utf-8")
        return destino

    return preparar


def test_la_configuracion_real_carga() -> None:
    config = cargar_config(CONFIG_REAL)
    assert config.umbrales.obra.capitulos == 10
    assert config.modelos.roles.redactor.id


def test_las_capas_suman_el_total() -> None:
    config = cargar_config(CONFIG_REAL)
    assert sum(config.umbrales.contexto.capas.model_dump().values()) == (
        config.umbrales.contexto.total
    )


def test_capas_que_no_suman_fallan(config_con: Callable[[Mutador], Path]) -> None:
    def mutar(u: dict[str, Any], m: dict[str, Any]) -> None:
        u["contexto"]["capas"]["local"] += 1

    with pytest.raises(ConfigInvalida, match=r"contexto.capas"):
        cargar_config(config_con(mutar))


def test_margen_menor_que_max_tokens_nombra_el_rol(
    config_con: Callable[[Mutador], Path],
) -> None:
    def mutar(u: dict[str, Any], m: dict[str, Any]) -> None:
        u["modelo"]["max_tokens_por_rol"]["judge"] = u["contexto"]["capas"]["margen"] + 1

    with pytest.raises(ConfigInvalida, match="judge"):
        cargar_config(config_con(mutar))


def test_umbral_semantico_nulo_con_cierre_falla_nombrando_la_clave(
    config_con: Callable[[Mutador], Path],
) -> None:
    def mutar(u: dict[str, Any], m: dict[str, Any]) -> None:
        u["medicion"]["cerrar_el_paso"] = True
        u["calidad"]["consistencia_factica"] = None

    with pytest.raises(ConfigInvalida, match=r"calidad\.consistencia_factica"):
        cargar_config(config_con(mutar))


def test_umbral_semantico_nulo_en_medicion_carga(
    config_con: Callable[[Mutador], Path],
) -> None:
    def mutar(u: dict[str, Any], m: dict[str, Any]) -> None:
        u["medicion"]["cerrar_el_paso"] = False
        u["calidad"]["consistencia_factica"] = None

    assert cargar_config(config_con(mutar)).umbrales.calidad.consistencia_factica is None


@pytest.mark.parametrize("cerrar", [True, False])
def test_umbral_que_cierra_siempre_nulo_falla(
    config_con: Callable[[Mutador], Path], cerrar: bool
) -> None:
    def mutar(u: dict[str, Any], m: dict[str, Any]) -> None:
        u["medicion"]["cerrar_el_paso"] = cerrar
        u["capitulo"]["longitud_min_palabras"] = None

    with pytest.raises(ConfigInvalida, match=r"capitulo\.longitud_min_palabras"):
        cargar_config(config_con(mutar))


def test_gate_lean_sin_timeout_falla(config_con: Callable[[Mutador], Path]) -> None:
    def mutar(u: dict[str, Any], m: dict[str, Any]) -> None:
        u["formal"]["gate_activo"] = True
        u["formal"]["lean_timeout_segundos"] = None

    with pytest.raises(ConfigInvalida, match=r"formal\.lean_timeout_segundos"):
        cargar_config(config_con(mutar))


def test_lean_incremental_sin_timeout_falla(config_con: Callable[[Mutador], Path]) -> None:
    def mutar(u: dict[str, Any], m: dict[str, Any]) -> None:
        u["formal"]["gate_activo"] = False
        u["formal"]["lean_incremental"] = True
        u["formal"]["lean_timeout_segundos"] = None

    with pytest.raises(ConfigInvalida, match=r"formal\.lean_incremental"):
        cargar_config(config_con(mutar))


def test_judge_igual_al_redactor_falla(config_con: Callable[[Mutador], Path]) -> None:
    def mutar(u: dict[str, Any], m: dict[str, Any]) -> None:
        m["roles"]["judge"]["id"] = m["roles"]["redactor"]["id"]

    with pytest.raises(ConfigInvalida, match="judge"):
        cargar_config(config_con(mutar))


def test_clave_desconocida_falla(config_con: Callable[[Mutador], Path]) -> None:
    def mutar(u: dict[str, Any], m: dict[str, Any]) -> None:
        u["contexto"]["capas"]["invariantes"] = 1

    with pytest.raises(ConfigInvalida, match="invariantes"):
        cargar_config(config_con(mutar))


def test_arranque_falla_con_umbral_nulo(
    config_con: Callable[[Mutador], Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    def mutar(u: dict[str, Any], m: dict[str, Any]) -> None:
        u["capitulo"]["longitud_max_palabras"] = None

    monkeypatch.setenv("STORYMAKER_CONFIG_DIR", str(config_con(mutar)))
    with (
        pytest.raises(ConfigInvalida, match=r"capitulo\.longitud_max_palabras"),
        TestClient(crear_app()),
    ):
        pass


def test_modelo_sin_precio_falla(config_con: Callable[[Mutador], Path]) -> None:
    def mutar(u: dict[str, Any], m: dict[str, Any]) -> None:
        m["roles"]["extractor"]["id"] = "claude-modelo-sin-precio"

    with pytest.raises(ConfigInvalida, match="claude-modelo-sin-precio"):
        cargar_config(config_con(mutar))
