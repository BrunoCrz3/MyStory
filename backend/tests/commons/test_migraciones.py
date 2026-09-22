"""H1 · prueba 1 — A-19, RNF-03.

Una migracion commiteada no se edita nunca (AGENTS.md regla 5). El hash aplicado
es lo unico que distingue una base reconstruida desde cero de una base que
aplico una version vieja del mismo fichero.

Los casos sinteticos parten de las migraciones reales en vez de inventarse una
001 propia: la tabla de control la crea la 001, asi que una secuencia que no
empiece por ella no es una secuencia de este sistema.
"""

import shutil
import sqlite3
from pathlib import Path

import pytest

from app.commons import errores
from app.commons.db import migraciones
from app.commons.db.conexion import Conexion


def _copia_de_las_reales(tmp_path: Path) -> tuple[Path, int]:
    directorio = tmp_path / "migrations"
    shutil.copytree(migraciones.DIRECTORIO_POR_DEFECTO, directorio)
    siguiente = len(migraciones.migraciones_disponibles(directorio)) + 1
    return directorio, siguiente


def _escribir(directorio: Path, nombre: str, sql: str) -> Path:
    directorio.mkdir(parents=True, exist_ok=True)
    fichero = directorio / nombre
    fichero.write_text(sql, encoding="utf-8")
    return fichero


def test_migraciones_se_aplican_en_orden_y_el_hash_cuadra(base_vacia: Conexion) -> None:
    aplicadas = migraciones.aplicar_migraciones(base_vacia)

    numeros = [m.numero for m in aplicadas]
    assert numeros, "el repositorio tiene al menos la migracion 001"
    assert numeros == sorted(numeros)
    assert numeros == list(range(1, len(numeros) + 1))

    registradas = migraciones.migraciones_aplicadas(base_vacia)
    assert [r.numero for r in registradas] == numeros
    assert [r.hash for r in registradas] == [m.hash for m in aplicadas]
    assert all(r.aplicada_en for r in registradas)

    assert migraciones.aplicar_migraciones(base_vacia) == []


def test_una_migracion_editada_despues_de_aplicarse_falla_en_voz_alta(
    base_vacia: Conexion, tmp_path: Path
) -> None:
    directorio, siguiente = _copia_de_las_reales(tmp_path)
    nombre = f"{siguiente:03d}_prueba.sql"
    _escribir(directorio, nombre, "CREATE TABLE prueba_a (id INTEGER PRIMARY KEY);")
    migraciones.aplicar_migraciones(base_vacia, directorio)

    _escribir(directorio, nombre, "CREATE TABLE prueba_b (id INTEGER PRIMARY KEY);")

    with pytest.raises(errores.MigracionEditada) as detalle:
        migraciones.aplicar_migraciones(base_vacia, directorio)
    assert f"{siguiente:03d}" in str(detalle.value)


def test_una_migracion_fuera_de_secuencia_no_se_aplica(
    base_vacia: Conexion, tmp_path: Path
) -> None:
    directorio, siguiente = _copia_de_las_reales(tmp_path)
    _escribir(
        directorio,
        f"{siguiente + 1:03d}_salto.sql",
        "CREATE TABLE prueba_c (id INTEGER PRIMARY KEY);",
    )

    with pytest.raises(errores.MigracionMalNumerada):
        migraciones.aplicar_migraciones(base_vacia, directorio)


def test_una_migracion_que_falla_no_deja_nada_a_medias(
    base_vacia: Conexion, tmp_path: Path
) -> None:
    directorio, siguiente = _copia_de_las_reales(tmp_path)
    _escribir(
        directorio,
        f"{siguiente:03d}_rota.sql",
        "CREATE TABLE prueba_a (id INTEGER PRIMARY KEY);\nESTO NO ES SQL;",
    )

    with pytest.raises(sqlite3.OperationalError):
        migraciones.aplicar_migraciones(base_vacia, directorio)

    tablas = {
        fila["name"]
        for fila in base_vacia.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert "prueba_a" not in tablas
    assert [r.numero for r in migraciones.migraciones_aplicadas(base_vacia)] == list(
        range(1, siguiente)
    )
