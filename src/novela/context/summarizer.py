"""Memoria media y reciente a partir de los resumenes del Archivista (§8, capas L3 y L4)."""

from __future__ import annotations

from novela.models import ChapterSummary
from novela.validators.length import count_units, prose_lines


def mid_summaries(summaries: list[ChapterSummary], upto: int) -> str:
    """Capa L3: resumenes de 1…i-2 en una linea cada uno."""
    selected = [item for item in summaries if item.number <= upto]
    if not selected:
        return ""
    return "\n".join(f"- Capítulo {item.number}: {item.one_line}" for item in selected)


def recent_summary(summaries: list[ChapterSummary], number: int) -> str:
    """Capa L4: resumen en parrafo del capitulo inmediatamente anterior."""
    for item in summaries:
        if item.number == number:
            return item.paragraph
    return ""


def literal_tail(text: str, unit: str, amount: int) -> str:
    """Cola literal del capitulo anterior, cortada por la unidad configurada.

    Reutiliza el contador canonico: aqui no se cuenta nada por cuenta propia (§18).
    """
    if amount <= 0 or not text.strip():
        return ""
    lines = prose_lines(text)
    if unit == "lines":
        return "\n".join(lines[-amount:])

    tail: list[str] = []
    for line in reversed(lines):
        tail.insert(0, line)
        if count_units("\n".join(tail), unit) >= amount:
            break
    return "\n".join(tail)
