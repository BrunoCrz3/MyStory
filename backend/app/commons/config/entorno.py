"""Comprobación de que el `.env` de la raíz llegó al entorno (TO-054).

El backend lee el `.env` con `uv run --env-file`, y uv descarta el fichero **entero** si no
sabe leer una línea (una ruta de Windows con barras invertidas sin comillas), con solo un
warning. Sin esta comprobación la app arrancaría sin Langfuse, sin servidor MCP —y entonces sin
publicar ninguna versión— y con otra base. Corre en el `lifespan`, así que cubre `python -m app`
y `uvicorn app.main:app --reload` por igual.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

ENV_DEL_REPO = Path(__file__).resolve().parents[4] / ".env"
# Para quien construye el entorno de otra forma: las pruebas y `python -m app --sin-env`.
VARIABLE_SIN_ENV = "STORYMAKER_SIN_ENV"


class EnvNoCargado(RuntimeError):
    """El `.env` existe y alguna de sus claves con valor no está en el entorno."""


def _claves_con_valor(ruta: Path) -> list[str]:
    claves = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        if valor.strip().strip("'\""):
            claves.append(clave.removeprefix("export ").strip())
    return claves


def comprobar_env(ruta: Path, entorno: Mapping[str, str]) -> None:
    """Toda clave con valor en el `.env` tiene que estar en el entorno. Nombra las que faltan,
    nunca sus valores."""
    if not ruta.is_file():
        return
    faltan = [clave for clave in _claves_con_valor(ruta) if not entorno.get(clave)]
    if faltan:
        raise EnvNoCargado(
            f"el .env de {ruta.parent} no llegó al entorno: faltan {', '.join(faltan)}. "
            "Arranca con `uv run --env-file ../.env …` desde backend/. Si ya lo haces, uv no "
            "supo leer alguna línea y descartó el fichero entero: una ruta de Windows va con "
            "barras normales (/) o entre comillas simples."
        )


def comprobar_env_del_repo() -> None:
    """La comprobación del arranque, salvo con `STORYMAKER_SIN_ENV`."""
    if os.environ.get(VARIABLE_SIN_ENV, "").strip():
        return
    comprobar_env(ENV_DEL_REPO, os.environ)
