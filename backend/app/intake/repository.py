"""SQL explícito del encargo. Nadie de fuera de `intake/` importa este módulo."""

from __future__ import annotations

import json
import sqlite3
import uuid

from app.intake.schemas import BriefNovela

SCHEMA_VERSION = "openapi-1.1.0#BriefNovela"


def insertar_brief(
    con: sqlite3.Connection, *, novel_id: str, brief: BriefNovela, ahora: str
) -> None:
    con.execute(
        "INSERT INTO brief_novela (novel_id, contenido, schema_version, validado_en)"
        " VALUES (?, ?, ?, ?)",
        (novel_id, brief.model_dump_json(), SCHEMA_VERSION, ahora),
    )
    c = brief.comprador
    con.execute(
        "INSERT INTO comprador (novel_id, identificador, relacion_con_destinatario)"
        " VALUES (?, ?, ?)",
        (novel_id, c.identificador, c.relacion_con_destinatario),
    )
    d = brief.destinatario
    con.execute(
        "INSERT INTO destinatario (novel_id, nombre, edad, rasgos, recuerdos, fecha_nacimiento)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            novel_id,
            d.nombre,
            d.edad,
            json.dumps(d.rasgos, ensure_ascii=False),
            json.dumps(d.recuerdos, ensure_ascii=False),
            d.fecha_nacimiento.isoformat() if d.fecha_nacimiento else None,
        ),
    )
    o = brief.ocasion
    con.execute(
        "INSERT INTO ocasion (novel_id, tipo, fecha, tono_esperado) VALUES (?, ?, ?, ?)",
        (novel_id, o.tipo, o.fecha.isoformat() if o.fecha else None, o.tono_esperado),
    )
    con.execute(
        "INSERT INTO dedicatoria (novel_id, texto, firma) VALUES (?, ?, ?)",
        (novel_id, brief.dedicatoria.texto, brief.dedicatoria.firma),
    )
    con.executemany(
        "INSERT INTO elemento_personalizado (id, novel_id, orden, enunciado, obligatorio, origen)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        [
            (uuid.uuid4().hex, novel_id, i, e.enunciado, int(e.obligatorio), e.origen)
            for i, e in enumerate(brief.elementos_personalizados)
        ],
    )
    con.executemany(
        "INSERT INTO texto_libre (id, novel_id, orden, contenido, procedencia)"
        " VALUES (?, ?, ?, ?, ?)",
        [
            (uuid.uuid4().hex, novel_id, i, t.contenido, t.procedencia)
            for i, t in enumerate(brief.textos_libres)
        ],
    )


def leer_brief(con: sqlite3.Connection, *, novel_id: str) -> BriefNovela | None:
    fila = con.execute(
        "SELECT contenido FROM brief_novela WHERE novel_id = ?", (novel_id,)
    ).fetchone()
    return None if fila is None else BriefNovela.model_validate_json(fila["contenido"])


def leer_elementos(con: sqlite3.Connection, *, novel_id: str) -> list[tuple[str, str, bool]]:
    filas = con.execute(
        "SELECT id, enunciado, obligatorio FROM elemento_personalizado WHERE novel_id = ?"
        " ORDER BY orden",
        (novel_id,),
    ).fetchall()
    return [(f["id"], f["enunciado"], bool(f["obligatorio"])) for f in filas]
