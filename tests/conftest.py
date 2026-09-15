"""Utilidades compartidas por la suite. Ningun test usa red ni clave de API."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def repo_root() -> Path:
    """Raiz real del repositorio, para los tests que leen config/ y fixtures/."""
    return REPO_ROOT


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    """Copia aislada del repositorio con config/, prompts/ y fixtures/ reales."""
    for name in ("config", "prompts", "fixtures"):
        shutil.copytree(REPO_ROOT / name, tmp_path / name)
    shutil.copyfile(REPO_ROOT / "novela.example.yaml", tmp_path / "novela.example.yaml")
    (tmp_path / "out").mkdir()
    return tmp_path


@pytest.fixture
def cli_in(sandbox: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Ejecuta la CLI contra el sandbox: la config se resuelve desde NOVELA_HOME."""
    monkeypatch.chdir(sandbox)
    monkeypatch.setenv("NOVELA_HOME", str(sandbox))
    return sandbox
