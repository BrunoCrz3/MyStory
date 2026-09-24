"""Barrido de secretos sobre el repositorio y los casetes (RNF-11, CLAUDE.md regla 12).

Como los demás comprobadores, recibe lo que barre y devuelve las violaciones, para que las
meta-pruebas lo ejecuten sobre ficheros escritos a propósito con un secreto.
"""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path

from tests.arquitectura.comprobadores import RAIZ_BACKEND, RAIZ_REPO

CASETES = RAIZ_BACKEND / "tests" / "casetes"
PLANTILLA_ENTORNO = RAIZ_REPO / ".env.example"
ENTORNO_LOCAL = RAIZ_REPO / ".env"

# Claves con su forma real: prefijo más cuerpo. El prefijo solo, sin cuerpo, aparece en la
# documentación y no es un secreto.
FORMAS_DE_CLAVE = (
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"\b(sk|pk)-lf-[A-Za-z0-9\-]{8,}"),
)
# Solo en casetes: ahí un nombre de cabecera de autenticación es la prueba de que se grabó.
CABECERAS_AUTENTICACION = re.compile(r"x-api-key|authorization", re.IGNORECASE)
# Qué variables de `.env.example` son secretas; las demás (entorno, rutas) no lo son.
NOMBRE_SECRETO = re.compile(r"KEY|SECRET|TOKEN|PASSWORD")
LONGITUD_MINIMA_VALOR = 8

# El entorno al importar, antes de que el fixture autouse vacíe las credenciales.
_ENTORNO_INICIAL = dict(os.environ)


def ficheros_a_barrer() -> list[Path]:
    """Lo versionado y lo que se versionaría (no ignorado), más todo casete."""
    salida = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=RAIZ_REPO,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    ficheros = {RAIZ_REPO / r for r in salida.split("\0") if r}
    if CASETES.is_dir():
        ficheros.update(p for p in CASETES.rglob("*") if p.is_file())
    return sorted(p for p in ficheros if p.is_file())


def _variables(fichero: Path) -> dict[str, str]:
    if not fichero.is_file():
        return {}
    variables: dict[str, str] = {}
    for linea in fichero.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        nombre, valor = linea.split("=", 1)
        variables[nombre.strip()] = valor.strip().strip("\"'")
    return variables


def valores_secretos(
    plantilla: Path = PLANTILLA_ENTORNO,
    local: Path = ENTORNO_LOCAL,
    entorno: Mapping[str, str] | None = None,
) -> set[str]:
    """Los valores reales de las variables secretas de la plantilla, del `.env` y del entorno."""
    nombres = {n for n in _variables(plantilla) if NOMBRE_SECRETO.search(n)}
    fuentes = [_variables(local), dict(entorno if entorno is not None else _ENTORNO_INICIAL)]
    return {
        valor
        for fuente in fuentes
        for nombre, valor in fuente.items()
        if nombre in nombres and len(valor) >= LONGITUD_MINIMA_VALOR
    }


def violaciones_secretos(ficheros: Iterable[Path], casetes: Path, valores: set[str]) -> list[str]:
    violaciones: list[str] = []
    for fichero in ficheros:
        texto = fichero.read_bytes().decode("utf-8", errors="ignore")
        if any(forma.search(texto) for forma in FORMAS_DE_CLAVE):
            violaciones.append(f"{fichero}: contiene una clave con forma de clave")
        if any(valor in texto for valor in valores):
            violaciones.append(f"{fichero}: contiene el valor de una variable secreta")
        if fichero.is_relative_to(casetes) and CABECERAS_AUTENTICACION.search(texto):
            violaciones.append(f"{fichero}: contiene una cabecera de autenticación")
    return violaciones
