#!/usr/bin/env python3
"""Ejecutor de tareas multiplataforma: Linux, macOS y Windows.

`Makefile` y `make.ps1` son envoltorios finos sobre este fichero. La definicion
de cada target vive aqui una sola vez, para que las dos rutas de invocacion no
puedan separarse (ver DECISIONS.md, D-14).

Solo usa la biblioteca estandar: `install` tiene que poder ejecutarse antes de
que exista el entorno virtual.

    python scripts/tasks.py verify
    python scripts/tasks.py lint test

Variables de entorno reconocidas:

    VENV    directorio del entorno virtual (por defecto `.venv`)

El interprete con el que se crea el entorno es el que ejecuta este script, asi
que `make install PY=python3.12` o `./make.ps1 install -Python py` eligen version.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IS_WINDOWS = os.name == "nt"

# Restos de ejecucion que `clean` borra, ademas del contenido de `out/`.
CLEAN_PATHS = (".pytest_cache", ".mypy_cache", ".ruff_cache", ".coverage", "htmlcov")

# Directorios que no se recorren buscando `__pycache__`.
PRUNED = frozenset({".git", ".venv", "venv", "out"})


class TaskError(RuntimeError):
    """Un paso de la tarea ha fallado. Aborta la ejecucion, nunca se ignora."""


# --------------------------------------------------------------------------
# Resolucion del entorno
# --------------------------------------------------------------------------


def venv_dir() -> Path:
    raw = Path(os.environ.get("VENV") or ".venv")
    return raw if raw.is_absolute() else ROOT / raw


def bin_dir() -> Path:
    """`Scripts` en Windows, `bin` en el resto. Es la unica diferencia de layout."""
    return venv_dir() / ("Scripts" if IS_WINDOWS else "bin")


def tool(name: str) -> str:
    """Ruta del ejecutable `name` en el entorno virtual, o el del PATH si no esta."""
    candidate = bin_dir() / (f"{name}.exe" if IS_WINDOWS else name)
    if candidate.is_file():
        return str(candidate)

    fallback = shutil.which(name)
    if fallback is None:
        raise TaskError(
            f"no se encuentra '{name}' ni en {bin_dir()} ni en el PATH. "
            f"Ejecuta primero la tarea 'install'."
        )
    print(f"[aviso] '{name}' no esta en {bin_dir()}; se usa {fallback} del PATH")
    return fallback


# --------------------------------------------------------------------------
# Primitivas
# --------------------------------------------------------------------------


def run(args: Sequence[str]) -> None:
    printable = " ".join(args)
    print(f"$ {printable}", flush=True)
    code = subprocess.run(args, cwd=ROOT, check=False).returncode
    if code != 0:
        raise TaskError(f"fallo con codigo {code}: {printable}")


def require_file(relative: str) -> None:
    """Equivalente portable de `test -f`."""
    print(f"$ comprobar {relative}", flush=True)
    if not (ROOT / relative).is_file():
        raise TaskError(f"falta el fichero esperado: {relative}")


def remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def pycache_dirs() -> Iterator[Path]:
    for path in ROOT.rglob("__pycache__"):
        if PRUNED.isdisjoint(path.relative_to(ROOT).parts):
            yield path


# --------------------------------------------------------------------------
# Targets
# --------------------------------------------------------------------------


def task_install() -> None:
    run([sys.executable, "-m", "venv", str(venv_dir())])
    python = tool("python")
    # `python -m pip`, no `pip`: en Windows el ejecutable no puede reescribirse
    # a si mismo mientras corre.
    run([python, "-m", "pip", "install", "--upgrade", "pip"])
    run([python, "-m", "pip", "install", "-e", ".[dev]"])


def task_demo() -> None:
    run([tool("python"), "-m", "novela", "demo"])


def task_test() -> None:
    run([tool("pytest"), "-q"])


def task_lint() -> None:
    ruff = tool("ruff")
    run([ruff, "check", "."])
    run([ruff, "format", "--check", "."])


def task_typecheck() -> None:
    run([tool("mypy"), "src/"])


def task_inventory() -> None:
    run([tool("python"), "scripts/check_inventory.py"])


def task_verify() -> None:
    task_inventory()
    task_lint()
    task_typecheck()
    task_test()
    task_demo()
    require_file("out/demo/manuscrito.md")
    run([tool("python"), "scripts/assert_demo_output.py"])


def task_clean() -> None:
    out = ROOT / "out"
    if out.is_dir():
        for entry in out.iterdir():
            if entry.name != ".gitkeep":
                remove(entry)
    for name in CLEAN_PATHS:
        remove(ROOT / name)
    for cache in pycache_dirs():
        remove(cache)
    out.mkdir(exist_ok=True)
    (out / ".gitkeep").touch()
    print("limpio.")


TASKS: dict[str, Callable[[], None]] = {
    "install": task_install,
    "demo": task_demo,
    "test": task_test,
    "lint": task_lint,
    "typecheck": task_typecheck,
    "inventory": task_inventory,
    "verify": task_verify,
    "clean": task_clean,
}


def usage() -> None:
    print("uso: python scripts/tasks.py <target> [<target>...]")
    print(f"targets: {', '.join(TASKS)}")


def main(argv: list[str]) -> int:
    if not argv:
        usage()
        return 0

    unknown = [name for name in argv if name not in TASKS]
    if unknown:
        print(f"ERROR: target desconocido: {', '.join(unknown)}", file=sys.stderr)
        usage()
        return 2

    for name in argv:
        try:
            TASKS[name]()
        except TaskError as error:
            print(f"ERROR: {name}: {error}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
