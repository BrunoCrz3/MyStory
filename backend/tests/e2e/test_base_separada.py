"""El backend con dobles nunca escribe en la base de la demo."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.commons.db import ruta_db
from app.commons.db.conexion import RAIZ_REPO
from tests.e2e.app_con_dobles import BASE_E2E_POR_DEFECTO, fijar_base_e2e


def test_con_la_env_de_la_demo_usa_su_propia_base(monkeypatch: pytest.MonkeyPatch) -> None:
    """Arrancado a mano con `--env-file ../.env`, ignora la base de la demo."""
    monkeypatch.setenv("STORYMAKER_DB_PATH", "data/storymaker.db")
    monkeypatch.delenv("STORYMAKER_E2E_DB_PATH", raising=False)
    fijar_base_e2e()
    assert ruta_db() == RAIZ_REPO / BASE_E2E_POR_DEFECTO
    assert ruta_db() != RAIZ_REPO / "data" / "storymaker.db"


def test_las_pruebas_le_dan_una_base_temporal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STORYMAKER_DB_PATH", "data/storymaker.db")
    monkeypatch.setenv("STORYMAKER_E2E_DB_PATH", str(tmp_path / "e2e.db"))
    fijar_base_e2e()
    assert ruta_db() == tmp_path / "e2e.db"
