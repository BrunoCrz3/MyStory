"""Ningún secreto en el repositorio ni en un casete (CLAUDE.md regla 12, RNF-11).

Dos barridos. En **todo fichero versionado o a punto de versionarse**: claves con forma de
clave del proveedor o de Langfuse, y el valor real de cualquier variable secreta de
`.env.example` que esté en el entorno o en `.env`. En **los casetes**, además, los nombres
de las cabeceras de autenticación, que ahí serían la prueba de que el grabador las dejó
pasar (A-50).
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.arquitectura.secretos import (
    CASETES,
    ficheros_a_barrer,
    valores_secretos,
    violaciones_secretos,
)


def test_ningun_fichero_versionado_ni_casete_contiene_secretos() -> None:
    violaciones = violaciones_secretos(ficheros_a_barrer(), CASETES, valores_secretos())
    assert violaciones == []


def test_el_barrido_incluye_los_ficheros_versionados_y_los_casetes() -> None:
    ficheros = {p.as_posix() for p in ficheros_a_barrer()}
    assert any(f.endswith("CLAUDE.md") for f in ficheros)
    assert any(f.endswith(".env.example") for f in ficheros)
    assert not any(f.endswith("/.env") for f in ficheros)


def test_un_casete_con_cabecera_de_autenticacion_hace_fallar(tmp_path: Path) -> None:
    casetes = tmp_path / "casetes"
    casetes.mkdir()
    for nombre, cabecera in (("a.json", "x-api-key"), ("b.json", "Authorization")):
        (casetes / nombre).write_text(
            json.dumps([{"peticion": {"cabeceras": {cabecera: "cualquier-cosa"}}}]),
            encoding="utf-8",
        )
    limpio = casetes / "c.json"
    limpio.write_text(json.dumps([{"peticion": {"cabeceras": {}}}]), encoding="utf-8")

    violaciones = violaciones_secretos(sorted(casetes.iterdir()), casetes, set())
    assert len(violaciones) == 2
    assert all("cabecera de autenticación" in v for v in violaciones)
    assert not any("c.json" in v for v in violaciones)


def test_una_clave_con_forma_de_clave_hace_fallar(tmp_path: Path) -> None:
    fichero = tmp_path / "config.py"
    fichero.write_text('CLAVE = "sk-ant-api03-' + "x" * 24 + '"\n', encoding="utf-8")
    langfuse = tmp_path / "lf.txt"
    langfuse.write_text("pk-lf-" + "0" * 12 + "\n", encoding="utf-8")
    violaciones = violaciones_secretos([fichero, langfuse], tmp_path / "casetes", set())
    assert len(violaciones) == 2


def test_el_valor_de_una_variable_secreta_hace_fallar(tmp_path: Path) -> None:
    fichero = tmp_path / "notas.md"
    fichero.write_text("la clave es valor-secreto-de-prueba\n", encoding="utf-8")
    violaciones = violaciones_secretos([fichero], tmp_path / "casetes", {"valor-secreto-de-prueba"})
    assert violaciones == [f"{fichero}: contiene el valor de una variable secreta"]


def test_los_valores_secretos_salen_de_las_variables_secretas_de_env_example(
    tmp_path: Path,
) -> None:
    plantilla = tmp_path / ".env.example"
    plantilla.write_text("ANTHROPIC_API_KEY=\nLANGFUSE_SECRET_KEY=\nSTORYMAKER_ENV=\n")
    env = tmp_path / ".env"
    env.write_text('LANGFUSE_SECRET_KEY="secreto-largo-1"\nSTORYMAKER_ENV=dev\n')
    valores = valores_secretos(
        plantilla, env, entorno={"ANTHROPIC_API_KEY": "secreto-largo-2", "STORYMAKER_ENV": "x"}
    )
    # `STORYMAKER_ENV` no es secreta: su valor aparece legítimamente en el repositorio.
    assert valores == {"secreto-largo-1", "secreto-largo-2"}
