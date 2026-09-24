"""SQL explícito de la obra. Nadie de fuera de `novel/` importa este módulo."""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from app.intake.service import BriefNovela
from app.novel.models import ReglaMundo

# Listar todas las novelas es, por definición, una consulta que no acota a una (A-02).
CONSULTAS_TRANSVERSALES = {"listar_obras", "contar_obras"}


def insertar_obra(
    con: sqlite3.Connection, *, novel_id: str, brief: BriefNovela, total: int, ahora: str
) -> None:
    con.execute(
        "INSERT INTO obra (novel_id, premisa, genero, tono, total_capitulos, creada_en)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (novel_id, brief.premisa, brief.genero, brief.tono, total, ahora),
    )
    con.executemany(
        "INSERT INTO regla_mundo (id, novel_id, orden, enunciado, origen)"
        " VALUES (?, ?, ?, ?, 'brief')",
        [(uuid.uuid4().hex, novel_id, i, r) for i, r in enumerate(brief.reglas_mundo)],
    )
    v = brief.voz_narrativa
    con.execute(
        "INSERT INTO voz_narrativa (novel_id, persona, tiempo_verbal, focalizacion)"
        " VALUES (?, ?, ?, ?)",
        (novel_id, v.persona, v.tiempo_verbal, v.focalizacion),
    )


def leer_obra(con: sqlite3.Connection, *, novel_id: str) -> dict[str, Any] | None:
    fila = con.execute(
        "SELECT novel_id, titulo, estado, total_capitulos, creada_en FROM obra WHERE novel_id = ?",
        (novel_id,),
    ).fetchone()
    return None if fila is None else dict(fila)


def listar_obras(
    con: sqlite3.Connection, *, limite: int, desplazamiento: int
) -> list[dict[str, Any]]:
    filas = con.execute(
        "SELECT novel_id, titulo, estado, creada_en FROM obra"
        " ORDER BY creada_en DESC, rowid DESC LIMIT ? OFFSET ?",
        (limite, desplazamiento),
    ).fetchall()
    return [dict(f) for f in filas]


def contar_obras(con: sqlite3.Connection) -> int:
    total: int = con.execute("SELECT count(*) FROM obra").fetchone()[0]
    return total


def leer_reglas(con: sqlite3.Connection, *, novel_id: str) -> list[ReglaMundo]:
    filas = con.execute(
        "SELECT enunciado, origen FROM regla_mundo WHERE novel_id = ? ORDER BY orden", (novel_id,)
    ).fetchall()
    return [ReglaMundo(enunciado=f["enunciado"], origen=f["origen"]) for f in filas]


def insertar_capitulo(con: sqlite3.Connection, *, novel_id: str, numero: int, version: int) -> str:
    capitulo_id = str(uuid.uuid4())
    con.execute(
        "INSERT INTO capitulo (id, novel_id, numero, version) VALUES (?, ?, ?, ?)",
        (capitulo_id, novel_id, numero, version),
    )
    return capitulo_id


def leer_capitulos_aceptados(
    con: sqlite3.Connection, *, novel_id: str, version: int
) -> list[dict[str, Any]]:
    """La fila vigente de cada capítulo aceptado en una versión: la de versión más alta que no
    la supera (D-05)."""
    filas = con.execute(
        "SELECT c.id, c.numero, c.titulo, c.texto FROM capitulo c"
        " WHERE c.novel_id = :novel_id AND c.estado = 'Aceptado' AND c.version = ("
        "   SELECT max(c2.version) FROM capitulo c2 WHERE c2.novel_id = c.novel_id"
        "   AND c2.numero = c.numero AND c2.version <= :version AND c2.estado = 'Aceptado')"
        " ORDER BY c.numero",
        {"novel_id": novel_id, "version": version},
    ).fetchall()
    return [dict(f) for f in filas]


def fijar_titulo(con: sqlite3.Connection, *, novel_id: str, titulo: str, premisa: str) -> None:
    con.execute(
        "UPDATE obra SET titulo = ?, premisa = coalesce(premisa, ?) WHERE novel_id = ?",
        (titulo, premisa, novel_id),
    )


def insertar_personaje(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    nombre: str,
    deseo: str,
    herida: str,
    rol_narrativo: str,
    voz: str,
    es_destinatario: bool,
    fecha_nacimiento: str | None,
) -> str:
    personaje_id = str(uuid.uuid4())
    con.execute(
        "INSERT INTO personaje (id, novel_id, nombre, deseo, herida, rol_narrativo, voz,"
        " fecha_nacimiento, es_destinatario) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            personaje_id,
            novel_id,
            nombre,
            deseo,
            herida,
            rol_narrativo,
            voz,
            fecha_nacimiento,
            int(es_destinatario),
        ),
    )
    return personaje_id


def insertar_lugar(
    con: sqlite3.Connection, *, novel_id: str, nombre: str, geografia: str, atmosfera: str
) -> str:
    lugar_id = str(uuid.uuid4())
    con.execute(
        "INSERT INTO lugar (id, novel_id, nombre, geografia, atmosfera) VALUES (?, ?, ?, ?, ?)",
        (lugar_id, novel_id, nombre, geografia, atmosfera),
    )
    return lugar_id


def insertar_hilo(
    con: sqlite3.Connection, *, novel_id: str, nombre: str, pregunta_dramatica: str
) -> None:
    con.execute(
        "INSERT INTO hilo_trama (id, novel_id, nombre, pregunta_dramatica) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), novel_id, nombre, pregunta_dramatica),
    )


def leer_personajes(con: sqlite3.Connection, *, novel_id: str) -> list[dict[str, Any]]:
    filas = con.execute(
        "SELECT id, nombre, deseo, herida, rol_narrativo, voz, es_destinatario, fecha_nacimiento"
        " FROM personaje WHERE novel_id = ? ORDER BY es_destinatario DESC, nombre",
        (novel_id,),
    ).fetchall()
    return [dict(f) for f in filas]


def leer_lugares(con: sqlite3.Connection, *, novel_id: str) -> list[dict[str, Any]]:
    filas = con.execute(
        "SELECT id, nombre, geografia, atmosfera FROM lugar WHERE novel_id = ? ORDER BY nombre",
        (novel_id,),
    ).fetchall()
    return [dict(f) for f in filas]


def leer_capitulo(
    con: sqlite3.Connection, *, novel_id: str, numero: int, version: int
) -> dict[str, Any] | None:
    fila = con.execute(
        "SELECT id, numero, version, estado, intentos, titulo, texto FROM capitulo"
        " WHERE novel_id = ? AND numero = ? AND version = ?",
        (novel_id, numero, version),
    ).fetchone()
    return None if fila is None else dict(fila)


def actualizar_estado_capitulo(
    con: sqlite3.Connection, *, novel_id: str, capitulo_id: str, estado: str, intentos: int
) -> None:
    con.execute(
        "UPDATE capitulo SET estado = ?, intentos = ? WHERE novel_id = ? AND id = ?",
        (estado, intentos, novel_id, capitulo_id),
    )


def devolver_a_pendiente(
    con: sqlite3.Connection, *, novel_id: str, version: int, estados: tuple[str, ...]
) -> list[int]:
    marcas = ", ".join("?" for _ in estados)
    filas = con.execute(
        f"UPDATE capitulo SET estado = 'Pendiente' WHERE novel_id = ? AND version = ?"
        f" AND estado IN ({marcas}) RETURNING numero",
        (novel_id, version, *estados),
    ).fetchall()
    return sorted(int(f["numero"]) for f in filas)


def sumar_consumo(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    capitulo_id: str,
    tokens_entrada: int,
    tokens_salida: int,
    coste_usd: float,
) -> None:
    con.execute(
        "UPDATE capitulo SET tokens_entrada = tokens_entrada + ?,"
        " tokens_salida = tokens_salida + ?, coste_usd = coste_usd + ?"
        " WHERE novel_id = ? AND id = ?",
        (tokens_entrada, tokens_salida, coste_usd, novel_id, capitulo_id),
    )


def guardar_texto_aceptado(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    capitulo_id: str,
    titulo: str,
    texto: str,
    palabras: int,
    gancho_cierre: str,
    momento: str,
    pov: str,
    lugar: str,
) -> None:
    con.execute(
        "UPDATE capitulo SET titulo = ?, texto = ?, palabras = ?, gancho_cierre = ?,"
        " aceptado_en = ?,"
        " pov_personaje_id = (SELECT id FROM personaje WHERE novel_id = ? AND nombre = ?),"
        " lugar_id = (SELECT id FROM lugar WHERE novel_id = ? AND nombre = ?)"
        " WHERE novel_id = ? AND id = ?",
        (
            titulo,
            texto,
            palabras,
            gancho_cierre,
            momento,
            novel_id,
            pov,
            novel_id,
            lugar,
            novel_id,
            capitulo_id,
        ),
    )


def insertar_evento(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    capitulo_id: str,
    descripcion: str,
    momento: int,
    lugar: str | None,
    personajes: list[str],
) -> None:
    evento_id = str(uuid.uuid4())
    con.execute(
        "INSERT INTO evento (id, novel_id, descripcion, momento, lugar_id) VALUES"
        " (?, ?, ?, ?, (SELECT id FROM lugar WHERE novel_id = ? AND nombre = ?))",
        (evento_id, novel_id, descripcion, momento, novel_id, lugar),
    )
    con.execute(
        "INSERT INTO evento_capitulo (novel_id, evento_id, capitulo_id) VALUES (?, ?, ?)",
        (novel_id, evento_id, capitulo_id),
    )
    for nombre in personajes:
        con.execute(
            "INSERT OR IGNORE INTO evento_personaje (novel_id, evento_id, personaje_id)"
            " SELECT ?, ?, id FROM personaje WHERE novel_id = ? AND nombre = ?",
            (novel_id, evento_id, novel_id, nombre),
        )


def insertar_elemento_en_capitulo(
    con: sqlite3.Connection, *, novel_id: str, elemento_id: str, capitulo_id: str
) -> None:
    con.execute(
        "INSERT OR IGNORE INTO elemento_capitulo (novel_id, elemento_id, capitulo_id)"
        " VALUES (?, ?, ?)",
        (novel_id, elemento_id, capitulo_id),
    )


def actualizar_estado_obra(con: sqlite3.Connection, *, novel_id: str, estado: str) -> None:
    con.execute("UPDATE obra SET estado = ? WHERE novel_id = ?", (estado, novel_id))


def contar_aceptados(con: sqlite3.Connection, *, novel_id: str, version: int) -> int:
    n: int = con.execute(
        "SELECT count(*) FROM capitulo WHERE novel_id = ? AND version = ? AND estado = 'Aceptado'",
        (novel_id, version),
    ).fetchone()[0]
    return n


def leer_estado_capitulo(con: sqlite3.Connection, *, novel_id: str, capitulo_id: str) -> str | None:
    fila = con.execute(
        "SELECT estado FROM capitulo WHERE novel_id = ? AND id = ?", (novel_id, capitulo_id)
    ).fetchone()
    return None if fila is None else str(fila["estado"])


def actualizar_solo_estado_capitulo(
    con: sqlite3.Connection, *, novel_id: str, capitulo_id: str, estado: str
) -> None:
    con.execute(
        "UPDATE capitulo SET estado = ? WHERE novel_id = ? AND id = ?",
        (estado, novel_id, capitulo_id),
    )
