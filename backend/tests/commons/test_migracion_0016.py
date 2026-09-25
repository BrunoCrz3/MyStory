"""Migración 0016: año, edad declarada y vigencia por versión del evento (TO-064, TO-066).

La historia sintética reproduce la de la base de la demo: la versión 1 publicada; una
regeneración de los capítulos 1 y 2 que se rechazó (versión 2, con su canon revertido,
TO-062); y otra del capítulo 2 publicada como versión 3 sobre la 1. Además, una novela cuya
primera versión se rechazó en el gate, que no se revierte.
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest

from app.commons.db import conectar
from app.commons.db.migrar import DIRECTORIO_MIGRACIONES, aplicar_migraciones

A = "novela-a"
B = "novela-b"


def _hasta(tmp_path: Path, numero: int) -> Path:
    d = tmp_path / f"hasta_{numero:04d}"
    d.mkdir()
    for f in sorted(DIRECTORIO_MIGRACIONES.glob("*.sql")):
        if int(f.stem[:4]) <= numero:
            shutil.copy(f, d / f.name)
    return d


def _obra(con: sqlite3.Connection, novel_id: str) -> None:
    con.execute(
        "INSERT INTO obra (novel_id, genero, tono, total_capitulos, creada_en)"
        " VALUES (?, 'g', 't', 2, '2026-09-25')",
        (novel_id,),
    )


def _capitulo(con: sqlite3.Connection, novel_id: str, cid: str, numero: int, version: int) -> None:
    con.execute(
        "INSERT INTO capitulo (id, novel_id, numero, version, estado, texto, aceptado_en)"
        " VALUES (?, ?, ?, ?, 'Aceptado', 'x', '2026-09-25')",
        (cid, novel_id, numero, version),
    )


def _evento(con: sqlite3.Connection, novel_id: str, eid: str, cid: str, momento: int) -> None:
    con.execute(
        "INSERT INTO evento (id, novel_id, descripcion, momento) VALUES (?, ?, 'e', ?)",
        (eid, novel_id, momento),
    )
    con.execute(
        "INSERT INTO evento_capitulo (novel_id, evento_id, capitulo_id) VALUES (?, ?, ?)",
        (novel_id, eid, cid),
    )


def _version(
    con: sqlite3.Connection,
    novel_id: str,
    version: int,
    estado: str,
    capitulos: dict[int, str],
    anterior: str | None = None,
) -> str:
    vid = f"{novel_id}-v{version}"
    con.execute(
        "INSERT INTO version_novela (id, novel_id, version, version_anterior_id, hash,"
        " publicada_en, estado) VALUES (?, ?, ?, ?, 'h', '2026-09-25', 'candidata')",
        (vid, novel_id, version, anterior),
    )
    for numero, cid in capitulos.items():
        con.execute(
            "INSERT INTO version_capitulo (novel_id, version, numero, capitulo_id, modificado)"
            " VALUES (?, ?, ?, ?, 0)",
            (novel_id, version, numero, cid),
        )
    con.execute("UPDATE version_novela SET estado = ? WHERE id = ?", (estado, vid))
    return vid


@pytest.fixture
def migrada(tmp_path: Path) -> sqlite3.Connection:
    con = conectar(tmp_path / "x.db")
    aplicar_migraciones(con, _hasta(tmp_path, 15))
    _obra(con, A)
    _capitulo(con, A, "a1v1", 1, 1)
    _capitulo(con, A, "a2v1", 2, 1)
    _capitulo(con, A, "a1v2", 1, 2)
    _capitulo(con, A, "a2v2", 2, 2)
    _capitulo(con, A, "a2v3", 2, 3)
    _evento(con, A, "e-a1v1", "a1v1", 101)
    _evento(con, A, "e-a2v1", "a2v1", 201)
    _evento(con, A, "e-a1v2", "a1v2", 101)
    _evento(con, A, "e-a2v2", "a2v2", 201)
    _evento(con, A, "e-a2v3", "a2v3", 201)
    v1 = _version(con, A, 1, "publicada", {1: "a1v1", 2: "a2v1"})
    _version(con, A, 2, "rechazada", {1: "a1v2", 2: "a2v2"}, anterior=v1)
    _version(con, A, 3, "publicada", {1: "a1v1", 2: "a2v3"}, anterior=v1)
    _obra(con, B)
    _capitulo(con, B, "b1v1", 1, 1)
    _evento(con, B, "e-b1v1", "b1v1", 101)
    _version(con, B, 1, "rechazada", {1: "b1v1"})
    con.commit()
    aplicar_migraciones(con)
    return con


def _vigencia(con: sqlite3.Connection, eid: str) -> tuple[int, int | None]:
    fila = con.execute(
        "SELECT version_desde, version_hasta FROM evento WHERE id = ?", (eid,)
    ).fetchone()
    return fila[0], fila[1]


def test_rellena_la_vigencia_desde_los_vinculos(migrada: sqlite3.Connection) -> None:
    assert _vigencia(migrada, "e-a1v1") == (1, None)
    assert _vigencia(migrada, "e-a2v1") == (1, 3)
    assert _vigencia(migrada, "e-a2v3") == (3, None)


def test_lo_de_una_regeneracion_rechazada_queda_vacio(migrada: sqlite3.Connection) -> None:
    assert _vigencia(migrada, "e-a1v2") == (2, 2)
    assert _vigencia(migrada, "e-a2v2") == (2, 2)


def test_una_primera_version_rechazada_conserva_sus_eventos(migrada: sqlite3.Connection) -> None:
    assert _vigencia(migrada, "e-b1v1") == (1, None)


def test_eventos_vigentes_coinciden_con_los_capitulos_de_cada_version_publicada(
    migrada: sqlite3.Connection,
) -> None:
    for version in (1, 3):
        vigentes = {
            r[0]
            for r in migrada.execute(
                "SELECT id FROM evento WHERE novel_id = ? AND version_desde <= ?"
                " AND (version_hasta IS NULL OR ? < version_hasta)",
                (A, version, version),
            )
        }
        por_vinculo = {
            r[0]
            for r in migrada.execute(
                "SELECT ec.evento_id FROM version_capitulo vc JOIN evento_capitulo ec"
                " ON ec.capitulo_id = vc.capitulo_id WHERE vc.novel_id = ? AND vc.version = ?",
                (A, version),
            )
        }
        assert vigentes == por_vinculo


def test_anio_y_edad_empiezan_vacios(migrada: sqlite3.Connection) -> None:
    assert migrada.execute("SELECT count(*) FROM evento WHERE anio IS NOT NULL").fetchone()[0] == 0
    assert (
        migrada.execute("SELECT count(*) FROM evento_personaje WHERE edad IS NOT NULL").fetchone()[
            0
        ]
        == 0
    )


def test_ningun_evento_nuevo_nace_sin_version(migrada: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError, match="version_desde"):
        migrada.execute(
            "INSERT INTO evento (id, novel_id, descripcion, momento) VALUES ('n', ?, 'e', 1)",
            (A,),
        )


def test_anio_y_edad_negativos_se_rechazan(migrada: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        migrada.execute("UPDATE evento SET anio = -1 WHERE id = 'e-a1v1'")
