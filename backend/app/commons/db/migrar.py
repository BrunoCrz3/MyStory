"""Runner de migraciones numeradas (RD-03).

Guarda el hash de cada migración aplicada y **falla en voz alta si una ya aplicada cambió**:
es lo que hace ejecutable «una migración commiteada no se edita nunca».

    uv run python -m app.commons.db.migrar
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import sys
from pathlib import Path

from app.commons.db.conexion import conectar, ruta_db

DIRECTORIO_MIGRACIONES = Path(__file__).resolve().parent / "migrations"
_NOMBRE = re.compile(r"^(\d{4})_[a-z0-9_]+$")


class MigracionEditada(RuntimeError):
    """Una migración ya aplicada no coincide con su fichero."""


def _hash(texto: str) -> str:
    # Se normalizan los finales de línea: git en Windows no puede cambiar el hash.
    return hashlib.sha256(texto.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def _ficheros(directorio: Path) -> list[Path]:
    ficheros = sorted(directorio.glob("*.sql"))
    for f in ficheros:
        if not _NOMBRE.match(f.stem):
            raise RuntimeError(f"migración con nombre inválido: {f.name} (NNNN_nombre.sql)")
    numeros = [f.stem[:4] for f in ficheros]
    if len(set(numeros)) != len(numeros):
        raise RuntimeError(f"números de migración repetidos en {directorio}")
    return ficheros


def aplicar_migraciones(
    con: sqlite3.Connection, directorio: Path = DIRECTORIO_MIGRACIONES
) -> list[str]:
    """Aplica las pendientes en orden y devuelve sus nombres."""
    con.execute(
        "CREATE TABLE IF NOT EXISTS _migracion ("
        " nombre TEXT PRIMARY KEY, hash TEXT NOT NULL,"
        " aplicada_en TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')))"
    )
    aplicadas = {r["nombre"]: r["hash"] for r in con.execute("SELECT nombre, hash FROM _migracion")}
    ficheros = _ficheros(directorio)
    presentes = {f.stem for f in ficheros}
    for nombre in aplicadas:
        if nombre not in presentes:
            raise MigracionEditada(f"la migración aplicada {nombre} ya no existe en {directorio}")

    nuevas: list[str] = []
    for f in ficheros:
        texto = f.read_text(encoding="utf-8")
        if f.stem in aplicadas:
            if aplicadas[f.stem] != _hash(texto):
                raise MigracionEditada(
                    f"la migración {f.stem} cambió después de aplicarse: no se edita, "
                    "se corrige con una migración nueva"
                )
            continue
        try:
            con.executescript(
                "BEGIN IMMEDIATE;\n"
                + texto
                + f"\n;INSERT INTO _migracion (nombre, hash) VALUES ('{f.stem}', '{_hash(texto)}');"
                + "\nCOMMIT;"
            )
        except sqlite3.Error:
            if con.in_transaction:
                con.execute("ROLLBACK")
            raise
        nuevas.append(f.stem)
    return nuevas


def main() -> int:
    ruta = ruta_db()
    con = conectar(ruta)
    try:
        nuevas = aplicar_migraciones(con)
    finally:
        con.close()
    print(
        f"{ruta}: {len(nuevas)} migraciones aplicadas"
        + (f" ({', '.join(nuevas)})" if nuevas else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
