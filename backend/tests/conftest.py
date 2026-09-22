"""Fixtures compartidas. Nada de mocks: bases reales en disco temporal."""

from collections.abc import Iterator
from pathlib import Path

import pytest

from app.commons.db import conexion as db
from app.commons.db.conexion import Conexion


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
