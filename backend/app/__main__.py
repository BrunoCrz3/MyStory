"""Lanzador: `uv run --env-file ../.env python -m app [--host H] [--port P] [--reload]
[--permitir-red] [--sin-env]`.

Hace tres cosas que `uvicorn` a secas no hace (D-11): **se niega a escuchar fuera de la
interfaz local** sin `--permitir-red`, porque no hay autenticación (RNF-12); **fija un solo
worker**, porque el pool en vuelo es un semáforo en proceso (RF-PROC-03); y **se niega a
arrancar si el `.env` de la raíz no llegó al entorno** (TO-054), porque uv descarta el fichero
entero cuando no sabe leer una línea y el backend arrancaría sin Langfuse, sin servidor MCP y con
otra base. `--sin-env` salta esa comprobación, para quien pasa el entorno de otra forma.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import uvicorn

LOCALES = frozenset({"127.0.0.1", "localhost", "::1"})
ENV_DEL_REPO = Path(__file__).resolve().parents[2] / ".env"


def validar_host(host: str, *, permitir_red: bool) -> None:
    if host not in LOCALES and not permitir_red:
        raise SystemExit(
            f"el backend no tiene autenticación y solo escucha en la interfaz local; "
            f"{host!r} no lo es. Usa --permitir-red si de verdad quieres exponerlo."
        )


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
        raise SystemExit(
            f"el .env de {ruta.parent} no llegó al entorno: faltan {', '.join(faltan)}. "
            "Arranca con `uv run --env-file ../.env python -m app`. Si ya lo haces, uv no supo "
            "leer alguna línea y descartó el fichero entero: una ruta de Windows va con barras "
            "normales (/) o entre comillas simples."
        )


def _parsear(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m app", description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--permitir-red", action="store_true")
    parser.add_argument("--sin-env", action="store_true")
    args = parser.parse_args(argv)
    validar_host(args.host, permitir_red=args.permitir_red)
    return args


def argumentos_uvicorn(argv: list[str]) -> dict[str, Any]:
    args = _parsear(argv)
    return {
        "app": "app.main:app",
        "host": args.host,
        "port": args.port,
        "reload": args.reload,
        "workers": 1,
    }


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if not _parsear(argv).sin_env:
        comprobar_env(ENV_DEL_REPO, os.environ)
    uvicorn.run(**argumentos_uvicorn(argv))


if __name__ == "__main__":
    main()
