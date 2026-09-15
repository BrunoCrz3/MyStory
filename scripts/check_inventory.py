#!/usr/bin/env python3
"""Valida `inventory.yaml` contra el arbol real del repositorio.

Comprueba, por cada grupo declarado:

1. Que cada ruta existe.
2. Que ningun fichero esta vacio.
3. Que ningun fichero de codigo o configuracion contiene marcadores de trabajo
   pendiente.
4. Que el numero de ficheros del grupo coincide con el contador declarado.

Sale con codigo 1 y la lista de incumplimientos si algo no cuadra.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

# Los marcadores se componen en tiempo de ejecucion para que este propio fichero
# no dispare la comprobacion que implementa.
MARKERS: tuple[str, ...] = (
    "TO" + "DO",
    "FIX" + "ME",
    "pass  # " + "placeholder",
)

# El escaneo de marcadores se aplica solo a codigo y configuracion. La
# documentacion (BUILD_SPEC.md, skills, prompts) cita esos marcadores de forma
# legitima.
SCANNED_SUFFIXES = frozenset({".py", ".yaml", ".yml", ".json", ".toml", ".sh"})


def load_inventory(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise SystemExit(f"inventory.yaml malformado: se esperaba un mapa, hay {type(data).__name__}")
    return data


def check_file(relative: str) -> list[str]:
    """Devuelve la lista de incumplimientos de un unico fichero."""
    problems: list[str] = []
    target = ROOT / relative
    if not target.exists():
        return [f"falta: {relative}"]
    if not target.is_file():
        return [f"no es un fichero: {relative}"]

    content = target.read_bytes()
    if not content.strip():
        problems.append(f"vacio: {relative}")

    if target.suffix in SCANNED_SUFFIXES:
        text = content.decode("utf-8", errors="replace")
        for marker in MARKERS:
            if marker in text:
                problems.append(f"marcador '{marker}' en {relative}")
    return problems


def check_group(group: dict[str, object]) -> tuple[str, int, list[str]]:
    name = str(group.get("name", "<sin nombre>"))
    files = group.get("files")
    if not isinstance(files, list):
        return name, 0, [f"grupo '{name}': la clave 'files' debe ser una lista"]

    problems: list[str] = []
    for entry in files:
        problems.extend(check_file(str(entry)))

    expected = group.get("expected")
    if isinstance(expected, int) and expected != len(files):
        problems.append(
            f"grupo '{name}': declara expected={expected} pero lista {len(files)} ficheros"
        )
    return name, len(files), problems


def main() -> int:
    inventory_path = ROOT / "inventory.yaml"
    if not inventory_path.exists():
        print("ERROR: no existe inventory.yaml en la raiz del repositorio", file=sys.stderr)
        return 1

    data = load_inventory(inventory_path)
    groups = data.get("groups")
    if not isinstance(groups, list):
        print("ERROR: inventory.yaml no declara una lista 'groups'", file=sys.stderr)
        return 1

    all_problems: list[str] = []
    total = 0
    for raw_group in groups:
        if not isinstance(raw_group, dict):
            all_problems.append("grupo malformado: se esperaba un mapa")
            continue
        name, count, problems = check_group(raw_group)
        total += count
        status = "OK " if not problems else "FALLA"
        print(f"[{status}] {name:<10} {count:>3} ficheros")
        all_problems.extend(problems)

    declared_total = data.get("total")
    if isinstance(declared_total, int) and total < declared_total:
        all_problems.append(f"total declarado {declared_total}, inventariados {total}")

    if all_problems:
        print(f"\n{len(all_problems)} incumplimiento(s):", file=sys.stderr)
        for problem in all_problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(f"\nInventario completo: {total} ficheros verificados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
