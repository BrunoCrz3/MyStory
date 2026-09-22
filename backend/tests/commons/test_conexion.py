"""H1 · prueba 2 — A-18, RNF-02.

`WAL` permite leer mientras se escribe, que es el patron del sistema: el
frontend consulta el canon mientras se consolida una escena. El punto ciego
declarado de A-18 es que una conexion abierta aparte puede no llevarlo, asi que
la prueba exige que la unica fabrica del repositorio lo active siempre.
"""

from pathlib import Path

from app.commons.db import conexion as db


def test_wal_esta_activado_en_la_conexion(ruta_de_base: Path) -> None:
    with db.abrir_conexion(ruta_de_base) as conexion:
        modo = conexion.execute("PRAGMA journal_mode").fetchone()[0]
    assert modo.lower() == "wal"


def test_las_claves_foraneas_estan_activadas(ruta_de_base: Path) -> None:
    with db.abrir_conexion(ruta_de_base) as conexion:
        activadas = conexion.execute("PRAGMA foreign_keys").fetchone()[0]
    assert activadas == 1


def test_no_hay_otra_forma_de_abrir_la_base_en_el_codigo() -> None:
    """El punto ciego de A-18: `sqlite3.connect` fuera de la fabrica."""
    raiz = Path(__file__).resolve().parents[2] / "app"
    culpables = [
        fichero
        for fichero in raiz.rglob("*.py")
        if "sqlite3.connect" in fichero.read_text(encoding="utf-8")
        and fichero != (raiz / "commons" / "db" / "conexion.py")
    ]
    assert culpables == []
