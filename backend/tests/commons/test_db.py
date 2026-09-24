"""Conexión, migraciones y transacciones (RD-01, RD-03, RD-04)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.commons.db import conectar, transaccion
from app.commons.db.migrar import DIRECTORIO_MIGRACIONES, MigracionEditada, aplicar_migraciones


def _migraciones(tmp_path: Path, **ficheros: str) -> Path:
    d = tmp_path / "migraciones"
    d.mkdir(exist_ok=True)
    for nombre, sql in ficheros.items():
        (d / f"{nombre}.sql").write_text(sql, encoding="utf-8")
    return d


def test_toda_conexion_tiene_wal_y_claves_foraneas(tmp_path: Path) -> None:
    con = conectar(tmp_path / "x.db")
    try:
        assert con.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        con.close()


def test_migraciones_en_orden_e_idempotentes(tmp_path: Path) -> None:
    d = _migraciones(
        tmp_path,
        **{
            "0002_b": "CREATE TABLE b (novel_id TEXT NOT NULL REFERENCES a(novel_id));",
            "0001_a": "CREATE TABLE a (novel_id TEXT PRIMARY KEY);",
        },
    )
    con = conectar(tmp_path / "x.db")
    try:
        assert aplicar_migraciones(con, d) == ["0001_a", "0002_b"]
        assert aplicar_migraciones(con, d) == []
    finally:
        con.close()


def test_editar_una_migracion_aplicada_falla(tmp_path: Path) -> None:
    d = _migraciones(tmp_path, **{"0001_a": "CREATE TABLE a (novel_id TEXT);"})
    con = conectar(tmp_path / "x.db")
    try:
        aplicar_migraciones(con, d)
        (d / "0001_a.sql").write_text("CREATE TABLE a (novel_id TEXT, x INT);", encoding="utf-8")
        with pytest.raises(MigracionEditada, match="0001_a"):
            aplicar_migraciones(con, d)
    finally:
        con.close()


def test_una_migracion_rota_no_deja_nada(tmp_path: Path) -> None:
    d = _migraciones(
        tmp_path, **{"0001_a": "CREATE TABLE a (novel_id TEXT);\nCREATE TABLE a (x INT);"}
    )
    con = conectar(tmp_path / "x.db")
    try:
        with pytest.raises(sqlite3.Error):
            aplicar_migraciones(con, d)
        tablas = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "a" not in tablas
    finally:
        con.close()


def test_transaccion_que_lanza_no_deja_filas(tmp_path: Path) -> None:
    con = conectar(tmp_path / "x.db")
    try:
        con.execute("CREATE TABLE t (novel_id TEXT)")
        with pytest.raises(RuntimeError), transaccion(con):
            con.execute("INSERT INTO t VALUES ('n1')")
            raise RuntimeError("a medias")
        assert con.execute("SELECT count(*) FROM t").fetchone()[0] == 0
        with transaccion(con):
            con.execute("INSERT INTO t VALUES ('n1')")
        assert con.execute("SELECT count(*) FROM t").fetchone()[0] == 1
    finally:
        con.close()


def test_toda_tabla_lleva_novel_id(tmp_path: Path) -> None:
    """RD-01 sobre las migraciones reales, presentes y futuras."""
    con = conectar(tmp_path / "real.db")
    try:
        aplicar_migraciones(con, DIRECTORIO_MIGRACIONES)
        tablas = [
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '\\_%' ESCAPE '\\'"
            )
        ]
        for tabla in tablas:
            columnas = {r[1]: r for r in con.execute(f"PRAGMA table_info({tabla})")}
            assert "novel_id" in columnas, f"{tabla} sin novel_id"
            assert columnas["novel_id"][3] == 1 or columnas["novel_id"][5] == 1, (
                f"{tabla}.novel_id admite NULL"
            )
            assert not {"user_id", "tenant_id"} & set(columnas), f"{tabla} con identidad"
    finally:
        con.close()
