"""SQL de `process/`: el esquema (restricciones de destino)."""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any


def insertar_restriccion(
    con: sqlite3.Connection, *, novel_id: str, numero: int, tipo: str, enunciado: str, alcance: str
) -> str:
    restriccion_id = str(uuid.uuid4())
    con.execute(
        "INSERT INTO restriccion_destino (id, novel_id, numero, tipo, enunciado, alcance)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (restriccion_id, novel_id, numero, tipo, enunciado, alcance),
    )
    return restriccion_id


def hay_esquema(con: sqlite3.Connection, *, novel_id: str) -> bool:
    return (
        con.execute("SELECT 1 FROM restriccion_destino WHERE novel_id = ?", (novel_id,)).fetchone()
        is not None
    )


# Reclamar el siguiente trabajo y contar la cola miran todas las novelas a la vez (A-02).
CONSULTAS_TRANSVERSALES = {
    "reclamar_siguiente",
    "contar_en_cola",
    "devolver_huerfanos",
    "leer_trabajo_por_id",
}


def trabajo_vivo(con: sqlite3.Connection, *, novel_id: str) -> str | None:
    fila = con.execute(
        "SELECT id FROM trabajo WHERE novel_id = ? AND estado_cola IN ('pendiente', 'en-curso')",
        (novel_id,),
    ).fetchone()
    return None if fila is None else str(fila["id"])


def insertar_trabajo(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    trabajo_id: str,
    tipo: str,
    estado: str,
    version_objetivo: int,
    estimacion: int,
    capitulos_a_regenerar: str,
    solicitud_id: str | None,
    ahora: str,
) -> None:
    con.execute(
        "INSERT INTO trabajo (id, novel_id, tipo, estado, version_objetivo, estimacion,"
        " capitulos_a_regenerar, solicitud_id, iniciada_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            trabajo_id,
            novel_id,
            tipo,
            estado,
            version_objetivo,
            estimacion,
            capitulos_a_regenerar,
            solicitud_id,
            ahora,
        ),
    )


def leer_trabajo(
    con: sqlite3.Connection, *, novel_id: str, trabajo_id: str
) -> dict[str, Any] | None:
    fila = con.execute(
        "SELECT t.*, k.ultimo_capitulo FROM trabajo t"
        " LEFT JOIN checkpoint k ON k.generacion_id = t.id"
        " WHERE t.novel_id = ? AND t.id = ?",
        (novel_id, trabajo_id),
    ).fetchone()
    return None if fila is None else dict(fila)


def listar_trabajos(con: sqlite3.Connection, *, novel_id: str) -> list[dict[str, Any]]:
    filas = con.execute(
        "SELECT t.*, k.ultimo_capitulo FROM trabajo t"
        " LEFT JOIN checkpoint k ON k.generacion_id = t.id"
        " WHERE t.novel_id = ? ORDER BY t.iniciada_en DESC, t.rowid DESC",
        (novel_id,),
    ).fetchall()
    return [dict(f) for f in filas]


def reclamar_siguiente(con: sqlite3.Connection) -> str | None:
    """Actualización condicional atómica: de dos reclamaciones a la vez, gana una (RF-PROC-03)."""
    fila = con.execute(
        "UPDATE trabajo SET estado_cola = 'en-curso'"
        " WHERE id = (SELECT id FROM trabajo WHERE estado_cola = 'pendiente'"
        "             ORDER BY iniciada_en, rowid LIMIT 1)"
        " AND estado_cola = 'pendiente' RETURNING id"
    ).fetchone()
    return None if fila is None else str(fila["id"])


def contar_en_cola(con: sqlite3.Connection) -> int:
    n: int = con.execute("SELECT count(*) FROM trabajo WHERE estado_cola = 'pendiente'").fetchone()[
        0
    ]
    return n


def devolver_huerfanos(con: sqlite3.Connection) -> list[str]:
    """Trabajos que estaban en curso cuando el proceso murió: vuelven a la cola, sin copia."""
    filas = con.execute(
        "UPDATE trabajo SET estado_cola = 'pendiente' WHERE estado_cola = 'en-curso' RETURNING id"
    ).fetchall()
    return [str(f["id"]) for f in filas]


def actualizar_trabajo(
    con: sqlite3.Connection, *, novel_id: str, trabajo_id: str, cambios: dict[str, Any]
) -> None:
    permitidas = {
        "estado_cola",
        "estado",
        "capitulo_actual",
        "intentos_infra",
        "tokens_consumidos",
        "coste_usd",
        "traza_langfuse_id",
        "detenida_por",
        "version_resultante",
        "terminada_en",
    }
    desconocidas = set(cambios) - permitidas
    if desconocidas:
        raise ValueError(f"columnas de trabajo no actualizables: {sorted(desconocidas)}")
    columnas = ", ".join(f"{c} = :{c}" for c in cambios)
    con.execute(
        f"UPDATE trabajo SET {columnas} WHERE novel_id = :novel_id AND id = :trabajo_id",
        {**cambios, "novel_id": novel_id, "trabajo_id": trabajo_id},
    )


def guardar_checkpoint(
    con: sqlite3.Connection, *, novel_id: str, trabajo_id: str, ultimo: int, ahora: str
) -> None:
    con.execute(
        "INSERT INTO checkpoint (generacion_id, novel_id, ultimo_capitulo, actualizado_en)"
        " VALUES (?, ?, ?, ?) ON CONFLICT (generacion_id) DO UPDATE SET"
        " ultimo_capitulo = excluded.ultimo_capitulo, actualizado_en = excluded.actualizado_en",
        (trabajo_id, novel_id, ultimo, ahora),
    )


def leer_trabajo_por_id(con: sqlite3.Connection, trabajo_id: str) -> dict[str, Any] | None:
    """Lo usa el worker: reclama un trabajo por id sin saber de qué novela es."""
    fila = con.execute("SELECT * FROM trabajo WHERE id = ?", (trabajo_id,)).fetchone()
    return None if fila is None else dict(fila)
