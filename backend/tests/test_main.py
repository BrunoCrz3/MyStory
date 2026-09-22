"""H1 - arranque de la aplicacion. A-39, RNF-12, RI-03."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main


def test_la_instancia_escucha_en_localhost_por_defecto() -> None:
    assert main.HOST_POR_DEFECTO == "127.0.0.1"


def test_el_openapi_se_publica(base_de_la_instancia: Path) -> None:
    with TestClient(main.app) as cliente:
        respuesta = cliente.get("/openapi.json")
    assert respuesta.status_code == 200
    assert respuesta.json()["openapi"].startswith("3.")


def test_el_arranque_aplica_las_migraciones_y_declara_la_fase(
    base_de_la_instancia: Path,
) -> None:
    with TestClient(main.app) as cliente:
        respuesta = cliente.get("/salud")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["fase_de_medicion"] is True
    assert cuerpo["ultima_migracion"] >= 1


@pytest.fixture
def base_de_la_instancia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ruta = tmp_path / "novel.db"
    monkeypatch.setenv("MYSTORY_DB", str(ruta))
    return ruta
