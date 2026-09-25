"""La aplicación falla en voz alta al arrancar si el `.env` no llegó al entorno (TO-054)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.__main__ import main
from app.commons.config import entorno
from app.commons.config.entorno import EnvNoCargado, comprobar_env
from app.main import crear_app

VALOR = "valor-que-no-debe-salir"


def _env(tmp_path: Path) -> Path:
    ruta = tmp_path / ".env"
    ruta.write_text(
        f"# comentario\nCLAVE_A={VALOR}\nCLAVE_VACIA=\n" + r"CLAVE_B='C:\zzoculto\x.exe'" + "\n",
        encoding="utf-8",
    )
    return ruta


def test_pasa_si_toda_clave_con_valor_esta_en_el_entorno(tmp_path: Path) -> None:
    comprobar_env(_env(tmp_path), {"CLAVE_A": "x", "CLAVE_B": "y"})


def test_falla_nombrando_las_claves_que_faltan_sin_mostrar_valores(tmp_path: Path) -> None:
    """Es lo que pasa cuando uv no sabe leer una línea: descarta el fichero entero."""
    with pytest.raises(EnvNoCargado) as fallo:
        comprobar_env(_env(tmp_path), {"CLAVE_A": "x"})
    mensaje = str(fallo.value)
    assert "CLAVE_B" in mensaje
    assert "CLAVE_A" not in mensaje
    assert "CLAVE_VACIA" not in mensaje
    assert VALOR not in mensaje and "zzoculto" not in mensaje
    assert "--env-file" in mensaje and "comillas simples" in mensaje


def test_sin_fichero_env_no_comprueba_nada(tmp_path: Path) -> None:
    comprobar_env(tmp_path / ".env", {})


def _env_sin_cargar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(entorno, "ENV_DEL_REPO", _env(tmp_path))
    monkeypatch.delenv(entorno.VARIABLE_SIN_ENV, raising=False)
    monkeypatch.delenv("CLAVE_A", raising=False)
    monkeypatch.delenv("CLAVE_B", raising=False)


def test_el_arranque_de_la_app_falla_si_el_env_no_llego(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """En el `lifespan`: cubre cualquier forma de arrancar la app, no solo el lanzador."""
    _env_sin_cargar(tmp_path, monkeypatch)
    with pytest.raises(EnvNoCargado, match="CLAVE_B"), TestClient(crear_app()):
        pass


def test_la_app_de_uvicorn_esta_cubierta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`uvicorn app.main:app --reload` y `python -m app` cargan este mismo objeto."""
    from app.main import app as app_de_uvicorn

    _env_sin_cargar(tmp_path, monkeypatch)
    with pytest.raises(EnvNoCargado), TestClient(app_de_uvicorn):
        pass


def test_sin_env_salta_la_comprobacion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _env_sin_cargar(tmp_path, monkeypatch)
    monkeypatch.setenv(entorno.VARIABLE_SIN_ENV, "1")
    with TestClient(crear_app()) as c:
        assert c.get("/salud").status_code == 200


def test_el_lanzador_traduce_sin_env_a_la_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(entorno.VARIABLE_SIN_ENV, raising=False)
    monkeypatch.setattr("app.__main__.uvicorn.run", lambda **_: None)
    main(["--sin-env"])
    import os

    assert os.environ[entorno.VARIABLE_SIN_ENV] == "1"
