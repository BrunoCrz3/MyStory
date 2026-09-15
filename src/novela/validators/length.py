"""Validador de longitud y CONTADOR CANONICO del sistema (BUILD_SPEC §3.5, §9.1).

Regla dura de §18: ningun otro modulo cuenta lineas ni palabras. Si necesitas un
recuento, llama a `count_units`.
"""

from __future__ import annotations

import re

from novela.models import LengthSpec
from novela.validators.base import ValidationReport, issue

#: Formatos prohibidos dentro del cuerpo de un capitulo (§9.1).
FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"^#", "encabezado Markdown"),
    (r"^\s*[-*•]\s", "viñeta"),
    (r"^\s*\d+[.)]\s", "numeración"),
)

HEADING_RE = re.compile(r"^\s*#")


def prose_lines(text: str) -> list[str]:
    """Lineas de prosa: sin blancos y sin el titulo del capitulo."""
    return [
        line.strip() for line in text.splitlines() if line.strip() and not HEADING_RE.match(line)
    ]


def count_units(text: str, unit: str) -> int:
    """Contador canonico. Una linea es una frase completa terminada en salto de linea."""
    lines = prose_lines(text)
    if unit == "lines":
        return len(lines)
    if unit == "words":
        return sum(len(line.split()) for line in lines)
    raise ValueError(f"unidad de longitud desconocida: '{unit}' (admitidas: lines, words)")


def forbidden_format(text: str) -> list[tuple[str, str]]:
    """Devuelve (linea, motivo) por cada formato prohibido encontrado."""
    found: list[tuple[str, str]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        for pattern, reason in FORBIDDEN_PATTERNS:
            if re.match(pattern, line):
                found.append((line.strip(), reason))
                break
    return found


def validate(text: str, spec: LengthSpec, *, chapter: int | None = None) -> ValidationReport:
    report = ValidationReport()
    counted = count_units(text, spec.unit)
    report.metrics[f"len.{spec.unit}"] = float(counted)

    low, high = spec.bounds()
    if not low <= counted <= high:
        report.issues.append(
            issue(
                "LEN-OUT-OF-RANGE",
                f"El capítulo tiene {counted} {spec.unit} y el plan exige entre {low} y {high}. "
                f"Reescríbelo hasta alcanzar exactamente {spec.target}.",
                chapter=chapter,
                evidence=f"{counted} {spec.unit}",
            )
        )

    for line, reason in forbidden_format(text):
        report.issues.append(
            issue(
                "LEN-FORBIDDEN-FORMAT",
                f"El cuerpo del capítulo contiene {reason}. La prosa no admite títulos, "
                "viñetas ni numeración: reescribe esa línea como una frase completa.",
                chapter=chapter,
                span=line[:80],
                evidence=reason,
            )
        )
    return report
