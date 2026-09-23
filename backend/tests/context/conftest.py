"""Fixtures de contexto: una obra consolidada e indexada."""

from collections.abc import Iterator
from pathlib import Path

import pytest

from app.commons.config import Umbrales
from app.commons.db.conexion import Conexion
from tests.canon.fabrica import Mundo
from tests.context import fabrica


@pytest.fixture
def base_indexada(base: Conexion) -> Iterator[tuple[Conexion, Mundo, list[int], Umbrales, int]]:
    umbrales = fabrica.umbrales()
    dimension = umbrales.embeddings.dimension
    assert dimension is not None, "H4 necesita la dimension declarada en thresholds.yaml"
    creado, escenas = fabrica.obra_indexada(base, dimension)
    yield base, creado, escenas, umbrales, dimension


__all__ = ["Path", "base_indexada"]
