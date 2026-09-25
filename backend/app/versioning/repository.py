"""SQL de `versioning/`: versiones —candidatas, publicadas o rechazadas—, sus vínculos y la
vista de lectura.

La vista de lectura une por SQL tablas de otras dueñas —capítulo, personaje, lugar, resumen,
brief de capítulo—: la story bible es una vista sobre tablas, y la regla de importación es de
módulos (A-20). Nada de aquí escribe fuera de `version_novela`, `version_capitulo` y
`exportacion`.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

# El historial mira todas las versiones de una novela a la vez: filtra por `novel_id`, y por
# `version` no puede (A-49).
# Al arrancar, los exports que quedaron `en-curso` de cualquier novela pasan a `fallido`.
CONSULTAS_TRANSVERSALES = {"listar_versiones", "interrumpir_exportaciones"}


def aceptados_de_version(
    con: sqlite3.Connection, *, novel_id: str, version: int
) -> dict[int, dict[str, Any]]:
    filas = con.execute(
        "SELECT id, numero, titulo, texto FROM capitulo"
        " WHERE novel_id = ? AND version = ? AND estado = 'Aceptado'",
        (novel_id, version),
    ).fetchall()
    return {int(f["numero"]): dict(f) for f in filas}


def vinculos(con: sqlite3.Connection, *, novel_id: str, version: int) -> dict[int, str]:
    filas = con.execute(
        "SELECT numero, capitulo_id FROM version_capitulo WHERE novel_id = ? AND version = ?",
        (novel_id, version),
    ).fetchall()
    return {int(f["numero"]): str(f["capitulo_id"]) for f in filas}


def contenido_de_capitulos(
    con: sqlite3.Connection, *, novel_id: str, ids: list[str]
) -> dict[str, dict[str, Any]]:
    marcas = ", ".join("?" for _ in ids)
    filas = con.execute(
        f"SELECT id, numero, titulo, texto FROM capitulo WHERE novel_id = ? AND id IN ({marcas})",
        (novel_id, *ids),
    ).fetchall()
    return {str(f["id"]): dict(f) for f in filas}


def obligatorios_ausentes(
    con: sqlite3.Connection, *, novel_id: str, capitulos: list[str]
) -> list[str]:
    marcas = ", ".join("?" for _ in capitulos) or "NULL"
    filas = con.execute(
        "SELECT e.enunciado FROM elemento_personalizado e"
        " WHERE e.novel_id = ? AND e.obligatorio = 1 AND NOT EXISTS ("
        "   SELECT 1 FROM elemento_capitulo ec WHERE ec.novel_id = e.novel_id"
        f"  AND ec.elemento_id = e.id AND ec.capitulo_id IN ({marcas}))"
        " ORDER BY e.orden",
        (novel_id, *capitulos),
    ).fetchall()
    return [str(f["enunciado"]) for f in filas]


def leer_version(con: sqlite3.Connection, *, novel_id: str, version: int) -> dict[str, Any] | None:
    fila = con.execute(
        "SELECT v.*, a.version AS version_anterior FROM version_novela v"
        " LEFT JOIN version_novela a ON a.id = v.version_anterior_id"
        " WHERE v.novel_id = ? AND v.version = ?",
        (novel_id, version),
    ).fetchone()
    return None if fila is None else dict(fila)


def version_base(con: sqlite3.Connection, *, novel_id: str, version: int) -> int | None:
    """La versión publicada de la que parte `version`: la más alta publicada por debajo. Una
    candidata rechazada nunca es base de otra (TO-062)."""
    fila = con.execute(
        "SELECT max(version) AS base FROM version_novela"
        " WHERE novel_id = ? AND estado = 'publicada' AND version < ?",
        (novel_id, version),
    ).fetchone()
    return None if fila is None or fila["base"] is None else int(fila["base"])


def siguiente_version(con: sqlite3.Connection, *, novel_id: str, version: int) -> int:
    """El número de la próxima candidata sobre la base `version`: el primero que no ha usado
    ninguna versión ni ninguna fila de capítulo, porque una rechazada conserva el suyo."""
    fila = con.execute(
        "SELECT max(coalesce((SELECT max(version) FROM version_novela WHERE novel_id = :n), 0),"
        " coalesce((SELECT max(version) FROM capitulo WHERE novel_id = :n), 0), :v) AS ultima",
        {"n": novel_id, "v": version},
    ).fetchone()
    return int(fila["ultima"]) + 1


def listar_versiones(con: sqlite3.Connection, *, novel_id: str) -> list[dict[str, Any]]:
    filas = con.execute(
        "SELECT v.*, a.version AS version_anterior FROM version_novela v"
        " LEFT JOIN version_novela a ON a.id = v.version_anterior_id"
        " WHERE v.novel_id = ? AND v.estado = 'publicada' ORDER BY v.version DESC",
        (novel_id,),
    ).fetchall()
    return [dict(f) for f in filas]


def modificados(con: sqlite3.Connection, *, novel_id: str, version: int) -> list[int]:
    filas = con.execute(
        "SELECT numero FROM version_capitulo"
        " WHERE novel_id = ? AND version = ? AND modificado = 1 ORDER BY numero",
        (novel_id, version),
    ).fetchall()
    return [int(f["numero"]) for f in filas]


def insertar_version(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    version: int,
    version_anterior_id: str | None,
    titulo: str | None,
    hash_contenido: str,
    motivo: str | None,
    generacion_id: str,
    ahora: str,
) -> str:
    version_id = str(uuid.uuid4())
    con.execute(
        "INSERT INTO version_novela (id, novel_id, version, version_anterior_id, titulo, hash,"
        " motivo, generacion_id, publicada_en, estado)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'candidata')",
        (
            version_id,
            novel_id,
            version,
            version_anterior_id,
            titulo,
            hash_contenido,
            motivo,
            generacion_id,
            ahora,
        ),
    )
    return version_id


def decidir_version(
    con: sqlite3.Connection, *, novel_id: str, version: int, estado: str, ahora: str
) -> None:
    """El gate decide: `candidata` pasa a `publicada` (con su fecha) o a `rechazada`. El
    trigger de la migración 0013 rechaza cualquier otro cambio."""
    con.execute(
        "UPDATE version_novela SET estado = ?,"
        " publicada_en = CASE WHEN ? = 'publicada' THEN ? ELSE publicada_en END"
        " WHERE novel_id = ? AND version = ? AND estado = 'candidata'",
        (estado, estado, ahora, novel_id, version),
    )


def insertar_vinculo(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    version: int,
    numero: int,
    capitulo_id: str,
    modificado: bool,
) -> None:
    con.execute(
        "INSERT INTO version_capitulo (novel_id, version, numero, capitulo_id, modificado)"
        " VALUES (?, ?, ?, ?, ?)",
        (novel_id, version, numero, capitulo_id, int(modificado)),
    )


def capitulos_de_version(
    con: sqlite3.Connection, *, novel_id: str, version: int
) -> list[dict[str, Any]]:
    filas = con.execute(
        "SELECT vc.numero, vc.modificado, c.titulo, c.estado, c.texto, c.palabras,"
        " c.gancho_cierre, c.intentos, r.texto AS resumen, p.nombre AS pov, l.nombre AS lugar,"
        " coalesce(c.funcion_dramatica, b.funcion_dramatica) AS funcion_dramatica"
        " FROM version_capitulo vc"
        " JOIN capitulo c ON c.id = vc.capitulo_id"
        " LEFT JOIN resumen_capitulo r ON r.capitulo_id = c.id"
        " LEFT JOIN personaje p ON p.id = c.pov_personaje_id"
        " LEFT JOIN lugar l ON l.id = c.lugar_id"
        " LEFT JOIN brief_capitulo b ON b.novel_id = vc.novel_id AND b.numero = vc.numero"
        " WHERE vc.novel_id = ? AND vc.version = ? ORDER BY vc.numero",
        (novel_id, version),
    ).fetchall()
    return [dict(f) for f in filas]


def insertar_solicitud(
    con: sqlite3.Connection,
    *,
    solicitud_id: str,
    novel_id: str,
    version_base: int,
    hecho_id: str | None,
    fragmento: str | None,
    hecho_candidato_id: str | None,
    enunciado_nuevo: str,
    capitulo_origen: int,
    ahora: str,
) -> None:
    con.execute(
        "INSERT INTO solicitud_cambio (id, novel_id, version_base, hecho_id, fragmento,"
        " hecho_candidato_id, enunciado_nuevo, capitulo_origen, creada_en)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            solicitud_id,
            novel_id,
            version_base,
            hecho_id,
            fragmento,
            hecho_candidato_id,
            enunciado_nuevo,
            capitulo_origen,
            ahora,
        ),
    )


def insertar_analisis(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    solicitud_id: str,
    capitulos: list[int],
    derivados: list[str],
    ahora: str,
) -> None:
    con.execute(
        "INSERT INTO analisis_impacto (id, novel_id, solicitud_id, capitulos_afectados,"
        " hechos_derivados, creado_en) VALUES (?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            novel_id,
            solicitud_id,
            json.dumps(capitulos),
            json.dumps(derivados),
            ahora,
        ),
    )


def leer_solicitud(
    con: sqlite3.Connection, *, novel_id: str, solicitud_id: str
) -> sqlite3.Row | None:
    fila: sqlite3.Row | None = con.execute(
        "SELECT s.*, a.capitulos_afectados, a.hechos_derivados FROM solicitud_cambio s"
        " LEFT JOIN analisis_impacto a ON a.solicitud_id = s.id AND a.novel_id = s.novel_id"
        " WHERE s.novel_id = ? AND s.id = ?",
        (novel_id, solicitud_id),
    ).fetchone()
    return fila


def fijar_estado_solicitud(
    con: sqlite3.Connection, *, novel_id: str, solicitud_id: str, estado: str
) -> None:
    con.execute(
        "UPDATE solicitud_cambio SET estado = ? WHERE novel_id = ? AND id = ?",
        (estado, novel_id, solicitud_id),
    )


def aplicar_solicitud(
    con: sqlite3.Connection, *, novel_id: str, solicitud_id: str, version_resultante: int
) -> None:
    con.execute(
        "UPDATE solicitud_cambio SET estado = 'aplicada', version_resultante = ?"
        " WHERE novel_id = ? AND id = ?",
        (version_resultante, novel_id, solicitud_id),
    )


def numeros_de_version(con: sqlite3.Connection, *, novel_id: str, version: int) -> list[int]:
    """Los capítulos que tienen fila propia en `version`: en una regeneración, los afectados,
    que nacen `Obsoleto` en la candidata al confirmar (TO-062)."""
    filas = con.execute(
        "SELECT numero FROM capitulo WHERE novel_id = ? AND version = ? ORDER BY numero",
        (novel_id, version),
    ).fetchall()
    return [int(f["numero"]) for f in filas]


# --- Export a PDF (P48) -------------------------------------------------------------------


def leer_exportacion(
    con: sqlite3.Connection, *, novel_id: str, version: int
) -> dict[str, Any] | None:
    fila = con.execute(
        "SELECT * FROM exportacion WHERE novel_id = ? AND version = ?", (novel_id, version)
    ).fetchone()
    return None if fila is None else dict(fila)


def iniciar_exportacion(
    con: sqlite3.Connection, *, novel_id: str, version: int, ahora: str
) -> None:
    """Un export nuevo, o el relanzamiento de uno fallido (A-119), queda `en-curso`."""
    con.execute(
        "INSERT INTO exportacion (novel_id, version, estado, solicitado_en)"
        " VALUES (?, ?, 'en-curso', ?)"
        " ON CONFLICT (novel_id, version) DO UPDATE SET estado = 'en-curso', ruta = NULL,"
        " generado_en = NULL, paridad_pdf_web = NULL, detalle = NULL,"
        " solicitado_en = excluded.solicitado_en WHERE exportacion.estado = 'fallido'",
        (novel_id, version, ahora),
    )


_COLUMNAS_CIERRE = frozenset({"estado", "ruta", "generado_en", "paridad_pdf_web", "detalle"})


def cerrar_exportacion(
    con: sqlite3.Connection, *, novel_id: str, version: int, cambios: dict[str, Any]
) -> None:
    assert set(cambios) <= _COLUMNAS_CIERRE, cambios
    asignaciones = ", ".join(f"{c} = ?" for c in cambios)
    con.execute(
        f"UPDATE exportacion SET {asignaciones}"
        " WHERE novel_id = ? AND version = ? AND estado = 'en-curso'",
        (*cambios.values(), novel_id, version),
    )


def interrumpir_exportaciones(con: sqlite3.Connection, *, ahora: str) -> None:
    con.execute(
        "UPDATE exportacion SET estado = 'fallido',"
        " detalle = 'interrumpido por un reinicio de la instancia a las ' || ?"
        " WHERE estado = 'en-curso'",
        (ahora,),
    )
