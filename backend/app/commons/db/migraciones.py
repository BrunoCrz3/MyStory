"""Runner de migraciones numeradas (RNF-03, A-19).

AGENTS.md regla 5: una migracion commiteada no se edita nunca. Editarla deja
bases divergentes que se ven identicas —una reconstruida desde cero, otra con la
version vieja aplicada— y el error aparece semanas despues y en otro sitio. El
hash de lo aplicado es lo unico que las distingue, asi que se guarda y se
compara en cada arranque.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.commons.db.conexion import Conexion
from app.commons.errores import MigracionEditada, MigracionMalNumerada

DIRECTORIO_POR_DEFECTO = Path(__file__).resolve().parent / "migrations"
TABLA_DE_CONTROL = "migracion_aplicada"
PATRON = re.compile(r"^(\d{3})_([a-z0-9_]+)\.sql$")


@dataclass(frozen=True)
class Migracion:
    numero: int
    nombre: str
    sql: str
    hash: str


@dataclass(frozen=True)
class RegistroDeMigracion:
    numero: int
    nombre: str
    hash: str
    aplicada_en: str


def _hash(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


def migraciones_disponibles(directorio: Path | None = None) -> list[Migracion]:
    origen = directorio or DIRECTORIO_POR_DEFECTO
    encontradas: list[Migracion] = []
    for fichero in sorted(origen.glob("*.sql")):
        coincide = PATRON.match(fichero.name)
        if not coincide:
            raise MigracionMalNumerada(f"'{fichero.name}' no sigue el patron NNN_nombre.sql")
        sql = fichero.read_text(encoding="utf-8")
        encontradas.append(
            Migracion(
                numero=int(coincide.group(1)),
                nombre=coincide.group(2),
                sql=sql,
                hash=_hash(sql),
            )
        )

    esperados = list(range(1, len(encontradas) + 1))
    if [m.numero for m in encontradas] != esperados:
        raise MigracionMalNumerada(
            f"la secuencia tiene huecos o repeticiones: {[m.numero for m in encontradas]}"
        )
    return encontradas


def _existe_la_tabla_de_control(conexion: Conexion) -> bool:
    fila = conexion.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (TABLA_DE_CONTROL,),
    ).fetchone()
    return fila is not None


def migraciones_aplicadas(conexion: Conexion) -> list[RegistroDeMigracion]:
    if not _existe_la_tabla_de_control(conexion):
        return []
    filas = conexion.execute(
        f"SELECT numero, nombre, hash, aplicada_en FROM {TABLA_DE_CONTROL} ORDER BY numero"
    ).fetchall()
    return [
        RegistroDeMigracion(
            numero=fila["numero"],
            nombre=fila["nombre"],
            hash=fila["hash"],
            aplicada_en=fila["aplicada_en"],
        )
        for fila in filas
    ]


def aplicar_migraciones(conexion: Conexion, directorio: Path | None = None) -> list[Migracion]:
    """Aplica en orden lo que falte y devuelve solo lo aplicado en esta llamada."""
    disponibles = migraciones_disponibles(directorio)
    ya_aplicadas = {registro.numero: registro for registro in migraciones_aplicadas(conexion)}

    for migracion in disponibles:
        registro = ya_aplicadas.get(migracion.numero)
        if registro is None:
            continue
        if registro.hash != migracion.hash:
            raise MigracionEditada(
                f"la migracion {migracion.numero:03d}_{migracion.nombre} cambio despues de "
                f"aplicarse: la base guarda {registro.hash[:12]} y el fichero es "
                f"{migracion.hash[:12]}. Una migracion commiteada no se edita: escribe otra."
            )

    pendientes = [m for m in disponibles if m.numero not in ya_aplicadas]
    for migracion in pendientes:
        _aplicar_una(conexion, migracion)
    return pendientes


def _aplicar_una(conexion: Conexion, migracion: Migracion) -> None:
    """Una migracion entra entera o no entra: SQLite tiene DDL transaccional."""
    try:
        conexion.executescript("BEGIN;\n" + migracion.sql)
        conexion.execute(
            f"INSERT INTO {TABLA_DE_CONTROL} (numero, nombre, hash, aplicada_en) "
            "VALUES (?, ?, ?, ?)",
            (
                migracion.numero,
                migracion.nombre,
                migracion.hash,
                datetime.now(UTC).isoformat(),
            ),
        )
    except BaseException:
        if conexion.in_transaction:
            conexion.execute("ROLLBACK")
        raise
    conexion.execute("COMMIT")
