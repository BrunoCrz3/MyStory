"""Fixtures compartidas. Nada de mocks: bases reales en disco temporal."""

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from app.commons.db import conexion as db
from app.commons.db.conexion import Conexion

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.fixture
def ruta_de_base(tmp_path: Path) -> Path:
    return tmp_path / "novel.db"


@pytest.fixture
def base_vacia(ruta_de_base: Path) -> Iterator[Conexion]:
    with db.abrir_conexion(ruta_de_base) as conexion:
        yield conexion


@pytest.fixture
def ruta_de_umbrales() -> Path:
    from app.commons.config import ruta_por_defecto_de_umbrales

    return ruta_por_defecto_de_umbrales()


@pytest.fixture
def base(ruta_de_base: Path) -> Iterator[Conexion]:
    """Base migrada al dia: es la que usa el sistema, no un esquema de prueba."""
    from app.commons.db import migraciones

    with db.abrir_conexion(ruta_de_base) as conexion:
        migraciones.aplicar_migraciones(conexion)
        yield conexion


@pytest.fixture
def cliente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator["TestClient"]:
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setenv("MYSTORY_DB", str(tmp_path / "novel.db"))
    with TestClient(app) as sesion:
        yield sesion
