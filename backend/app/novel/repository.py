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


def insertar_capitulo(
    con: sqlite3.Connection, *, novel_id: str, numero: int, version: int, estado: str = "Pendiente"
) -> str:
    capitulo_id = str(uuid.uuid4())
    con.execute(
        "INSERT INTO capitulo (id, novel_id, numero, version, estado) VALUES (?, ?, ?, ?, ?)",
        (capitulo_id, novel_id, numero, version, estado),
    )
    return capitulo_id


# Las filas que puede leer la versión `:version`: las suyas y las de las versiones publicadas.
# Una candidata rechazada no es base de nada: sus filas no las lee ninguna otra versión (TO-062).
_FILA_LEGIBLE = (
    "({a}.version = :version OR {a}.version IN (SELECT vn.version FROM version_novela vn"
    " WHERE vn.novel_id = :novel_id AND vn.estado = 'publicada'))"
)


def leer_capitulos_aceptados(
    con: sqlite3.Connection, *, novel_id: str, version: int
) -> list[dict[str, Any]]:
    """La fila vigente de cada capítulo aceptado en una versión: la de versión más alta que no
    la supera (D-05), entre las que esa versión puede leer (TO-062)."""
    filas = con.execute(
        "SELECT c.id, c.numero, c.titulo, c.texto FROM capitulo c"
        " WHERE c.novel_id = :novel_id AND c.estado = 'Aceptado' AND c.version = ("
        "   SELECT max(c2.version) FROM capitulo c2 WHERE c2.novel_id = c.novel_id"
        "   AND c2.numero = c.numero AND c2.version <= :version AND c2.estado = 'Aceptado'"
        f"   AND {_FILA_LEGIBLE.format(a='c2')})"
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
    version: int,
    descripcion: str,
    momento: int,
    lugar: str | None,
    personajes: list[str],
    anio: int | None,
    edades: dict[str, int],
) -> None:
    evento_id = str(uuid.uuid4())
    con.execute(
        "INSERT INTO evento (id, novel_id, descripcion, momento, anio, version_desde, lugar_id)"
        " VALUES (?, ?, ?, ?, ?, ?, (SELECT id FROM lugar WHERE novel_id = ? AND nombre = ?))",
        (evento_id, novel_id, descripcion, momento, anio, version, novel_id, lugar),
    )
    con.execute(
        "INSERT INTO evento_capitulo (novel_id, evento_id, capitulo_id) VALUES (?, ?, ?)",
        (novel_id, evento_id, capitulo_id),
    )
    for nombre in personajes:
        con.execute(
            "INSERT OR IGNORE INTO evento_personaje (novel_id, evento_id, personaje_id, edad)"
            " SELECT ?, ?, id, ? FROM personaje WHERE novel_id = ? AND nombre = ?",
            (novel_id, evento_id, edades.get(nombre), novel_id, nombre),
        )


def insertar_excluyente(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    capitulo_id: str,
    version: int,
    personaje: str,
    tipo: str,
    momento: int,
) -> bool:
    """Liga el excluyente al evento vigente del capítulo en ese `momento`, si el personaje
    existe. Devuelve si se ligó: sin evento o sin personaje no se inventa nada."""
    cursor = con.execute(
        "INSERT OR IGNORE INTO evento_excluyente (novel_id, evento_id, personaje_id, tipo)"
        " SELECT :novel_id, e.id, p.id, :tipo FROM evento e"
        " JOIN evento_capitulo ec ON ec.evento_id = e.id AND ec.capitulo_id = :capitulo_id"
        " JOIN personaje p ON p.novel_id = e.novel_id AND p.nombre = :personaje"
        f" WHERE e.novel_id = :novel_id AND e.momento = :momento AND {_vigente('e')}",
        {
            "novel_id": novel_id,
            "capitulo_id": capitulo_id,
            "personaje": personaje,
            "tipo": tipo,
            "momento": momento,
            "version": version,
        },
    )
    return cursor.rowcount > 0


def _vigente(alias: str) -> str:
    """Vigencia semiabierta, la misma que la del hecho (TO-028, TO-066)."""
    return (
        f"{alias}.version_desde <= :version AND "
        f"({alias}.version_hasta IS NULL OR :version < {alias}.version_hasta)"
    )


def leer_eventos_de_version(
    con: sqlite3.Connection, *, novel_id: str, version: int
) -> list[dict[str, Any]]:
    """Eventos vigentes en `version`, con su capítulo, en orden de narración."""
    filas = con.execute(
        "SELECT e.id, e.momento, e.anio, e.lugar_id, ec.capitulo_id, c.numero"
        " FROM evento e JOIN evento_capitulo ec ON ec.evento_id = e.id"
        " JOIN capitulo c ON c.id = ec.capitulo_id"
        f" WHERE e.novel_id = :novel_id AND {_vigente('e')}"
        " ORDER BY e.momento, e.id",
        {"novel_id": novel_id, "version": version},
    ).fetchall()
    return [dict(f) for f in filas]


def leer_presencias(
    con: sqlite3.Connection, *, novel_id: str, version: int
) -> list[tuple[str, str, int | None]]:
    """`(evento_id, personaje_id, edad)` de los eventos vigentes en `version`."""
    filas = con.execute(
        "SELECT ep.evento_id, ep.personaje_id, ep.edad FROM evento_personaje ep"
        " JOIN evento e ON e.id = ep.evento_id"
        f" WHERE ep.novel_id = :novel_id AND {_vigente('e')}"
        " ORDER BY ep.evento_id, ep.personaje_id",
        {"novel_id": novel_id, "version": version},
    ).fetchall()
    return [(str(f[0]), str(f[1]), f[2]) for f in filas]


def leer_excluyentes(
    con: sqlite3.Connection, *, novel_id: str, version: int
) -> list[tuple[str, str, str]]:
    """`(evento_id, personaje_id, tipo)` de los excluyentes de eventos vigentes en `version`:
    heredan la vigencia de su evento."""
    filas = con.execute(
        "SELECT x.evento_id, x.personaje_id, x.tipo FROM evento_excluyente x"
        " JOIN evento e ON e.id = x.evento_id"
        f" WHERE x.novel_id = :novel_id AND {_vigente('e')}"
        " ORDER BY x.evento_id, x.personaje_id",
        {"novel_id": novel_id, "version": version},
    ).fetchall()
    return [(str(f[0]), str(f[1]), str(f[2])) for f in filas]


def retirar_eventos(
    con: sqlite3.Connection, *, novel_id: str, capitulo_id: str, version: int
) -> None:
    """Los eventos que narraba la fila vieja dejan de estar vigentes desde `version`."""
    con.execute(
        "UPDATE evento SET version_hasta = ?"
        " WHERE novel_id = ? AND version_hasta IS NULL AND id IN"
        " (SELECT evento_id FROM evento_capitulo WHERE novel_id = ? AND capitulo_id = ?)",
        (version, novel_id, novel_id, capitulo_id),
    )


def revertir_eventos(con: sqlite3.Connection, *, novel_id: str, version: int) -> None:
    """Deshace lo que `version` escribió en la fábula, como `canon` en el canon (TO-062): lo
    que abrió queda con intervalo vacío y lo que cerró vuelve a estar abierto."""
    con.execute(
        "UPDATE evento SET version_hasta = version_desde WHERE novel_id = ? AND version_desde = ?",
        (novel_id, version),
    )
    con.execute(
        "UPDATE evento SET version_hasta = NULL"
        " WHERE novel_id = ? AND version_hasta = ? AND version_desde < ?",
        (novel_id, version, version),
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


def leer_capitulo_anterior(
    con: sqlite3.Connection, *, novel_id: str, numero: int, version: int
) -> str | None:
    fila = con.execute(
        "SELECT c.id FROM capitulo c WHERE c.novel_id = :novel_id AND c.numero = :numero"
        f" AND c.version < :version AND {_FILA_LEGIBLE.format(a='c')}"
        " ORDER BY c.version DESC LIMIT 1",
        {"novel_id": novel_id, "numero": numero, "version": version},
    ).fetchone()
    return None if fila is None else str(fila["id"])


def leer_apariciones(
    con: sqlite3.Connection, *, novel_id: str, capitulo_ids: list[str]
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """`(nombre, capitulo_id)` de personajes y de lugares que aparecen en esos capítulos: por
    los eventos que narran y por el POV y el lugar del propio capítulo."""
    if not capitulo_ids:
        return [], []
    marcas = ", ".join("?" for _ in capitulo_ids)
    personajes = con.execute(
        "SELECT p.nombre, ec.capitulo_id FROM evento_capitulo ec"
        " JOIN evento_personaje ep ON ep.evento_id = ec.evento_id AND ep.novel_id = ec.novel_id"
        " JOIN personaje p ON p.id = ep.personaje_id"
        f" WHERE ec.novel_id = ? AND ec.capitulo_id IN ({marcas})"
        " UNION SELECT p.nombre, c.id FROM capitulo c JOIN personaje p ON p.id = c.pov_personaje_id"
        f" WHERE c.novel_id = ? AND c.id IN ({marcas})",
        (novel_id, *capitulo_ids, novel_id, *capitulo_ids),
    ).fetchall()
    lugares = con.execute(
        "SELECT l.nombre, ec.capitulo_id FROM evento_capitulo ec"
        " JOIN evento e ON e.id = ec.evento_id JOIN lugar l ON l.id = e.lugar_id"
        f" WHERE ec.novel_id = ? AND ec.capitulo_id IN ({marcas})"
        " UNION SELECT l.nombre, c.id FROM capitulo c JOIN lugar l ON l.id = c.lugar_id"
        f" WHERE c.novel_id = ? AND c.id IN ({marcas})",
        (novel_id, *capitulo_ids, novel_id, *capitulo_ids),
    ).fetchall()
    return (
        [(str(f[0]), str(f[1])) for f in personajes],
        [(str(f[0]), str(f[1])) for f in lugares],
    )
