"""Lanzador: `uv run --env-file ../.env python -m app [--host H] [--port P] [--reload]
[--permitir-red] [--sin-env]`.

Hace dos cosas que `uvicorn` a secas no hace (D-11): **se niega a escuchar fuera de la
interfaz local** sin `--permitir-red`, porque no hay autenticación (RNF-12), y **fija un solo
worker**, porque el pool en vuelo es un semáforo en proceso (RF-PROC-03). La comprobación de
que el `.env` llegó al entorno no está aquí sino en el `lifespan` de la app (TO-054), para que
cubra también `uvicorn --reload`; `--sin-env` la salta.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

import uvicorn

from app.commons.config.entorno import VARIABLE_SIN_ENV

LOCALES = frozenset({"127.0.0.1", "localhost", "::1"})


def validar_host(host: str, *, permitir_red: bool) -> None:
    if host not in LOCALES and not permitir_red:
        raise SystemExit(
            f"el backend no tiene autenticación y solo escucha en la interfaz local; "
            f"{host!r} no lo es. Usa --permitir-red si de verdad quieres exponerlo."
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
    if _parsear(argv).sin_env:
        # Por el entorno y no por argumento: con --reload, la app corre en otro proceso.
        os.environ[VARIABLE_SIN_ENV] = "1"
    uvicorn.run(**argumentos_uvicorn(argv))


if __name__ == "__main__":
    main()
