#!/usr/bin/env python3
"""Verifica el manuscrito de la demo (BUILD_SPEC §21.11).

Comprueba que `out/demo/manuscrito.md` tiene exactamente los capitulos y la
longitud que pide la configuracion efectiva. Usa `count_units`, nunca un
contador propio (§18).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from novela.config import project_dir, resolve  # noqa: E402
from novela.validators.length import count_units  # noqa: E402

CHAPTER_RE = re.compile(r"^## Capítulo (\d+) — (.+)$")


def split_chapters(markdown: str) -> list[tuple[int, str]]:
    chapters: list[tuple[int, str]] = []
    number: int | None = None
    body: list[str] = []
    for line in markdown.splitlines():
        match = CHAPTER_RE.match(line)
        if match:
            if number is not None:
                chapters.append((number, "\n".join(body)))
            number, body = int(match.group(1)), []
        elif number is not None:
            body.append(line)
    if number is not None:
        chapters.append((number, "\n".join(body)))
    return chapters


def main() -> int:
    bundle = resolve(repo_root=ROOT, flags={"llm.provider": "fake", "profile": "micro"}, environ={})
    spec = bundle.config.novel.length
    expected_chapters = bundle.config.novel.chapters

    path = project_dir(ROOT, "demo") / "manuscrito.md"
    if not path.is_file():
        print(f"ERROR: no existe {path}. Ejecuta `python -m novela demo`.", file=sys.stderr)
        return 1

    chapters = split_chapters(path.read_text(encoding="utf-8"))
    problems: list[str] = []
    if len(chapters) != expected_chapters:
        problems.append(
            f"el manuscrito tiene {len(chapters)} capítulos y se esperaban {expected_chapters}"
        )

    low, high = spec.bounds()
    for number, body in chapters:
        counted = count_units(body, spec.unit)
        if not low <= counted <= high:
            problems.append(
                f"capítulo {number}: {counted} {spec.unit}, se esperaban entre {low} y {high}"
            )

    if problems:
        print("El manuscrito de la demo no cumple el contrato:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(
        f"manuscrito.md correcto: {len(chapters)} capítulos de {spec.target} {spec.unit} cada uno."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
