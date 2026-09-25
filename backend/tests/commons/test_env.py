"""El lanzador falla en voz alta si el `.env` no llegó al entorno."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.__main__ import argumentos_uvicorn, comprobar_env

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
    with pytest.raises(SystemExit) as fallo:
        comprobar_env(_env(tmp_path), {"CLAVE_A": "x"})
    mensaje = str(fallo.value)
    assert "CLAVE_B" in mensaje
    assert "CLAVE_A" not in mensaje
    assert "CLAVE_VACIA" not in mensaje
    assert VALOR not in mensaje and "zzoculto" not in mensaje
    assert "--env-file" in mensaje and "comillas simples" in mensaje


def test_sin_fichero_env_no_comprueba_nada(tmp_path: Path) -> None:
    comprobar_env(tmp_path / ".env", {})


def test_sin_env_es_una_opcion_del_lanzador() -> None:
    assert argumentos_uvicorn(["--sin-env"])["port"] == 8000
