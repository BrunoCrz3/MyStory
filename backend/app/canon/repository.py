"""SQL explícito de la story bible. Nadie de fuera de `canon/` importa este módulo.

Toda consulta por versión se resuelve por vigencia (D-06): la condición está escrita una
sola vez, en `_vigente()`, para que ninguna consulta la reescriba a su manera. Las lecturas
cruzan con `capitulo` por SQL para devolver números de capítulo: la story bible es la vista
consolidada sobre las tablas de `canon/` y `novel/` (A-20).
"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from app.canon.models import Hecho, HechoNuevo, Promesa, PromesaNueva, Snapshot

# Consultas que cruzan versiones a propósito (A-02, RD-02): el retcon de una solicitud
# nombra dos hechos por su id, el viejo y el nuevo, que viven en versiones distintas.
CONSULTAS_TRANSVERSALES = {"leer_retcon"}


def _vigente(alias: str) -> str:
    return (
        f"{alias}.version_desde <= :version AND "
        f"({alias}.version_hasta IS NULL OR :version < {alias}.version_hasta)"
    )


def ya_consolidado(
    con: sqlite3.Connection, *, novel_id: str, version: int, capitulo_id: str
) -> bool:
    fila = con.execute(
        "SELECT 1 FROM snapshot s JOIN capitulo c ON c.id = s.capitulo_id"
        " WHERE s.novel_id = ? AND s.capitulo_id = ? AND c.version <= ?",
        (novel_id, capitulo_id, version),
    ).fetchone()
    return fila is not None


def insertar_hecho_propuesto(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    version: int,
    capitulo_id: str,
    hecho: HechoNuevo,
    ahora: str,
) -> str:
    hecho_id = str(uuid.uuid4())
    con.execute(
        "INSERT INTO hecho (id, novel_id, enunciado, tipo, estado, origen, fragmento_soporte,"
        " capitulo_establece_id, version_desde, creado_en)"
        " VALUES (?, ?, ?, ?, 'propuesto', 'extraccion', ?, ?, ?, ?)",
        (
            hecho_id,
            novel_id,
            hecho.enunciado,
            hecho.tipo,
            hecho.fragmento_soporte,
            capitulo_id,
            version,
            ahora,
        ),
    )
    return hecho_id


def adoptar_hecho(con: sqlite3.Connection, *, novel_id: str, version: int, hecho_id: str) -> None:
    con.execute(
        "UPDATE hecho SET estado = 'adoptado' WHERE novel_id = ? AND id = ? AND version_desde = ?",
        (novel_id, hecho_id, version),
    )


def descartar_hecho(con: sqlite3.Connection, *, novel_id: str, version: int, hecho_id: str) -> None:
    # Intervalo vacío: un hecho descartado no es vigente en ninguna versión (D-06).
    con.execute(
        "UPDATE hecho SET estado = 'descartado', version_hasta = version_desde"
        " WHERE novel_id = ? AND id = ? AND version_desde = ?",
        (novel_id, hecho_id, version),
    )


def insertar_uso(
    con: sqlite3.Connection, *, novel_id: str, version: int, hecho_id: str, capitulo_id: str
) -> None:
    con.execute(
        "INSERT OR IGNORE INTO hecho_capitulo (novel_id, hecho_id, capitulo_id, version_desde)"
        " VALUES (?, ?, ?, ?)",
        (novel_id, hecho_id, capitulo_id, version),
    )


def hecho_es_vigente(
    con: sqlite3.Connection, *, novel_id: str, version: int, hecho_id: str
) -> bool:
    fila = con.execute(
        f"SELECT 1 FROM hecho h WHERE h.novel_id = :novel_id AND h.id = :hecho_id"
        f" AND {_vigente('h')}",
        {"novel_id": novel_id, "hecho_id": hecho_id, "version": version},
    ).fetchone()
    return fila is not None


def insertar_promesa(
    con: sqlite3.Connection, *, novel_id: str, capitulo_id: str, promesa: PromesaNueva
) -> str:
    promesa_id = str(uuid.uuid4())
    con.execute(
        "INSERT INTO promesa (id, novel_id, enunciado, tipo) VALUES (?, ?, ?, ?)",
        (promesa_id, novel_id, promesa.enunciado, promesa.tipo),
    )
    vincular_promesa(
        con, novel_id=novel_id, promesa_id=promesa_id, capitulo_id=capitulo_id, papel="apertura"
    )
    return promesa_id


def vincular_promesa(
    con: sqlite3.Connection, *, novel_id: str, promesa_id: str, capitulo_id: str, papel: str
) -> None:
    """Una fila de capítulo abre o paga una promesa (TO-047). Nunca se modifica un vínculo:
    la fila nueva de una regeneración añade el suyo y la vieja conserva el que tenía."""
    con.execute(
        "INSERT OR IGNORE INTO promesa_capitulo (novel_id, promesa_id, capitulo_id, papel)"
        " SELECT ?, ?, ?, ? WHERE EXISTS (SELECT 1 FROM promesa WHERE id = ? AND novel_id = ?)",
        (novel_id, promesa_id, capitulo_id, papel, promesa_id, novel_id),
    )


def insertar_snapshot(
    con: sqlite3.Connection, *, novel_id: str, capitulo_id: str, snapshot: Snapshot, ahora: str
) -> None:
    con.execute(
        "INSERT INTO snapshot (id, novel_id, capitulo_id, contenido, creado_en)"
        " VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), novel_id, capitulo_id, snapshot.model_dump_json(), ahora),
    )


def leer_snapshot(
    con: sqlite3.Connection, *, novel_id: str, version: int, capitulo_id: str
) -> Snapshot | None:
    fila = con.execute(
        "SELECT s.contenido FROM snapshot s JOIN capitulo c ON c.id = s.capitulo_id"
        " WHERE s.novel_id = ? AND s.capitulo_id = ? AND c.version <= ?",
        (novel_id, capitulo_id, version),
    ).fetchone()
    return None if fila is None else Snapshot.model_validate_json(fila["contenido"])


def _usos(con: sqlite3.Connection, *, novel_id: str, version: int) -> dict[str, list[int]]:
    filas = con.execute(
        f"SELECT u.hecho_id, c.numero FROM hecho_capitulo u JOIN capitulo c ON c.id = u.capitulo_id"
        f" WHERE u.novel_id = :novel_id AND {_vigente('u')} ORDER BY c.numero",
        {"novel_id": novel_id, "version": version},
    ).fetchall()
    usos: dict[str, list[int]] = {}
    for f in filas:
        usos.setdefault(f["hecho_id"], []).append(f["numero"])
    return usos


def leer_hechos_vigentes(
    con: sqlite3.Connection, *, novel_id: str, version: int, hasta_numero: int | None = None
) -> list[Hecho]:
    parametros: dict[str, Any] = {"novel_id": novel_id, "version": version}
    filtro = ""
    if hasta_numero is not None:
        filtro = " AND (c.numero IS NULL OR c.numero <= :hasta)"
        parametros["hasta"] = hasta_numero
    filas = con.execute(
        "SELECT h.id, h.enunciado, h.tipo, h.estado, h.origen, h.fragmento_soporte,"
        " c.numero AS establece FROM hecho h LEFT JOIN capitulo c ON c.id = h.capitulo_establece_id"
        f" WHERE h.novel_id = :novel_id AND {_vigente('h')}{filtro}"
        " ORDER BY coalesce(c.numero, 0), h.creado_en, h.id",
        parametros,
    ).fetchall()
    usos = _usos(con, novel_id=novel_id, version=version)
    return [
        Hecho(
            hecho_id=f["id"],
            enunciado=f["enunciado"],
            tipo=f["tipo"],
            estado=f["estado"],
            origen=f["origen"],
            capitulo_establece=f["establece"],
            capitulos_usan=usos.get(f["id"], []),
            fragmento_soporte=f["fragmento_soporte"],
        )
        for f in filas
    ]


def leer_capitulos_que_usan(
    con: sqlite3.Connection, *, novel_id: str, version: int, hecho_id: str
) -> list[int]:
    filas = con.execute(
        f"SELECT DISTINCT c.numero FROM hecho_capitulo u JOIN capitulo c ON c.id = u.capitulo_id"
        f" WHERE u.novel_id = :novel_id AND u.hecho_id = :hecho_id AND {_vigente('u')}"
        " ORDER BY c.numero",
        {"novel_id": novel_id, "hecho_id": hecho_id, "version": version},
    ).fetchall()
    return [f["numero"] for f in filas]


def leer_promesas(
    con: sqlite3.Connection, *, novel_id: str, capitulo_ids: list[str]
) -> list[Promesa]:
    """Las promesas que ven unas filas de capítulo —las de una versión— con su estado en ellas.

    Una promesa está en la versión si alguna de sus filas la abre **o la paga**: la que
    abría una fila reescrita y paga una no afectada sigue viva aunque la nueva no la reabra;
    solo desaparece si ninguna fila de la versión la abre ni la paga (TO-047). Su apertura es
    la de la versión, o la de la fila que la abrió si ya no está.
    """
    if not capitulo_ids:
        return []
    marcas = ",".join("?" for _ in capitulo_ids)
    filas = con.execute(
        "SELECT p.id, p.enunciado, p.tipo,"
        " coalesce("
        "   (SELECT min(c.numero) FROM promesa_capitulo v JOIN capitulo c ON c.id = v.capitulo_id"
        f"    WHERE v.promesa_id = p.id AND v.papel = 'apertura' AND v.capitulo_id IN ({marcas})),"
        "   (SELECT min(c.numero) FROM promesa_capitulo v JOIN capitulo c ON c.id = v.capitulo_id"
        "    WHERE v.promesa_id = p.id AND v.papel = 'apertura')) AS apertura,"
        " (SELECT min(c.numero) FROM promesa_capitulo v JOIN capitulo c ON c.id = v.capitulo_id"
        f"  WHERE v.promesa_id = p.id AND v.papel = 'pago' AND v.capitulo_id IN ({marcas})) AS pago"
        " FROM promesa p WHERE p.novel_id = ? AND EXISTS ("
        "   SELECT 1 FROM promesa_capitulo v WHERE v.promesa_id = p.id"
        f"   AND v.capitulo_id IN ({marcas}))"
        " ORDER BY apertura, p.rowid",
        (*capitulo_ids, *capitulo_ids, novel_id, *capitulo_ids),
    ).fetchall()
    return [
        Promesa(
            promesa_id=f["id"],
            enunciado=f["enunciado"],
            tipo=f["tipo"],
            estado="pendiente" if f["pago"] is None else "pagada",
            capitulo_apertura=f["apertura"],
            capitulo_pago=f["pago"],
        )
        for f in filas
    ]


def existe_novela(con: sqlite3.Connection, *, novel_id: str) -> bool:
    return con.execute("SELECT 1 FROM obra WHERE novel_id = ?", (novel_id,)).fetchone() is not None


def existe_version(con: sqlite3.Connection, *, novel_id: str, version: int) -> bool:
    """Una versión publicada. Como el JOIN con `capitulo` (A-20), la lectura cruza una tabla
    de otra feature por SQL: `canon/` no importa `versioning/` (A-93)."""
    fila = con.execute(
        "SELECT 1 FROM version_novela WHERE novel_id = ? AND version = ?", (novel_id, version)
    ).fetchone()
    return fila is not None


def retirar_capitulo(
    con: sqlite3.Connection, *, novel_id: str, capitulo_id: str, version: int
) -> None:
    con.execute(
        "UPDATE hecho_capitulo SET version_hasta = ?"
        " WHERE novel_id = ? AND capitulo_id = ? AND version_hasta IS NULL",
        (version, novel_id, capitulo_id),
    )
    con.execute(
        "UPDATE hecho SET version_hasta = ?"
        " WHERE novel_id = ? AND capitulo_establece_id = ? AND version_hasta IS NULL"
        " AND NOT EXISTS (SELECT 1 FROM hecho_capitulo u WHERE u.hecho_id = hecho.id"
        "   AND u.novel_id = hecho.novel_id AND u.version_hasta IS NULL)",
        (version, novel_id, capitulo_id),
    )


def revertir_version(con: sqlite3.Connection, *, novel_id: str, version: int) -> None:
    """Deshace lo que la versión `version` escribió en el canon: lo que abrió se queda con un
    intervalo vacío y lo que cerró vuelve a estar abierto (TO-062). El orden respeta RD-05: los
    usos caben siempre en la vigencia de su hecho."""
    con.execute(
        "UPDATE hecho_capitulo SET version_hasta = version_desde"
        " WHERE novel_id = ? AND version_desde = ?",
        (novel_id, version),
    )
    con.execute(
        "UPDATE hecho SET version_hasta = version_desde WHERE novel_id = ? AND version_desde = ?",
        (novel_id, version),
    )
    con.execute(
        "UPDATE hecho SET version_hasta = NULL,"
        " estado = CASE estado WHEN 'retconeado' THEN 'adoptado' ELSE estado END"
        " WHERE novel_id = ? AND version_hasta = ? AND version_desde < ?",
        (novel_id, version, version),
    )
    con.execute(
        "UPDATE hecho_capitulo SET version_hasta = NULL"
        " WHERE novel_id = ? AND version_hasta = ? AND version_desde < ?",
        (novel_id, version, version),
    )


def leer_retcon(
    con: sqlite3.Connection, *, novel_id: str, solicitud_id: str
) -> tuple[str, str] | None:
    fila = con.execute(
        "SELECT v.enunciado AS viejo, n.enunciado AS nuevo FROM retcon r"
        " JOIN hecho v ON v.id = r.hecho_viejo_id JOIN hecho n ON n.id = r.hecho_nuevo_id"
        " WHERE r.novel_id = ? AND r.solicitud_id = ?",
        (novel_id, solicitud_id),
    ).fetchone()
    return None if fila is None else (str(fila["viejo"]), str(fila["nuevo"]))
