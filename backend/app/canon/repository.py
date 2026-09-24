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
        "INSERT INTO promesa (id, novel_id, enunciado, tipo, capitulo_apertura_id)"
        " VALUES (?, ?, ?, ?, ?)",
        (promesa_id, novel_id, promesa.enunciado, promesa.tipo, capitulo_id),
    )
    return promesa_id


def pagar_promesa(
    con: sqlite3.Connection, *, novel_id: str, capitulo_id: str, promesa_id: str
) -> None:
    con.execute(
        "UPDATE promesa SET estado = 'pagada', capitulo_pago_id = ?"
        " WHERE novel_id = ? AND id = ? AND estado = 'pendiente'",
        (capitulo_id, novel_id, promesa_id),
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
    con: sqlite3.Connection, *, novel_id: str, version: int, capitulo_ids: list[str]
) -> list[Promesa]:
    """Promesas abiertas en los capítulos de una versión, con su estado en esa versión."""
    if not capitulo_ids:
        return []
    marcas = ",".join("?" for _ in capitulo_ids)
    filas = con.execute(
        "SELECT p.id, p.enunciado, p.tipo, ca.numero AS apertura, cp.numero AS pago,"
        f" p.capitulo_pago_id IN ({marcas}) AS pagada_aqui"
        " FROM promesa p JOIN capitulo ca ON ca.id = p.capitulo_apertura_id"
        " LEFT JOIN capitulo cp ON cp.id = p.capitulo_pago_id"
        f" WHERE p.novel_id = ? AND p.capitulo_apertura_id IN ({marcas}) AND ca.version <= ?"
        " ORDER BY ca.numero, p.id",
        (*capitulo_ids, novel_id, *capitulo_ids, version),
    ).fetchall()
    return [
        Promesa(
            promesa_id=f["id"],
            enunciado=f["enunciado"],
            tipo=f["tipo"],
            estado="pagada" if f["pagada_aqui"] else "pendiente",
            capitulo_apertura=f["apertura"],
            capitulo_pago=f["pago"] if f["pagada_aqui"] else None,
        )
        for f in filas
    ]


def promesas_pendientes_hasta(
    con: sqlite3.Connection, *, novel_id: str, version: int, numero: int
) -> list[str]:
    filas = con.execute(
        "SELECT p.enunciado FROM promesa p JOIN capitulo ca ON ca.id = p.capitulo_apertura_id"
        " LEFT JOIN capitulo cp ON cp.id = p.capitulo_pago_id"
        " WHERE p.novel_id = ? AND ca.version <= ? AND ca.numero <= ?"
        " AND (cp.id IS NULL OR cp.numero > ?)"
        " ORDER BY ca.numero, p.id",
        (novel_id, version, numero, numero),
    ).fetchall()
    return [f["enunciado"] for f in filas]
