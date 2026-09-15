"""T-01: el contador canonico del sistema."""

from __future__ import annotations

import pytest

from novela.models import LengthSpec
from novela.validators import length

TEXT = """## Capítulo 1 — Título

El hielo crujía bajo la rejilla.

Nadia revisó el sello del guante izquierdo.
"""


def test_count_lines_ignores_blanks_and_title() -> None:
    assert length.count_units(TEXT, "lines") == 2


def test_count_words_ignores_blanks_and_title() -> None:
    assert length.count_units(TEXT, "words") == 13


def test_unknown_unit_is_loud() -> None:
    with pytest.raises(ValueError, match="unidad de longitud desconocida"):
        length.count_units(TEXT, "paragraphs")


@pytest.mark.parametrize(
    ("line", "reason"),
    [
        ("- una viñeta", "viñeta"),
        ("1. numerada", "numeración"),
        ("# encabezado", "encabezado Markdown"),
    ],
)
def test_forbidden_format_is_detected(line: str, reason: str) -> None:
    found = length.forbidden_format(f"Una frase normal.\n{line}\n")
    assert [item[1] for item in found] == [reason]


def test_out_of_range_is_blocking() -> None:
    spec = LengthSpec(unit="lines", target=4, tolerance=0)
    report = length.validate("Una sola frase.\n", spec, chapter=1)
    assert [issue.code for issue in report.blocking] == ["LEN-OUT-OF-RANGE"]
    assert report.metrics["len.lines"] == 1.0


def test_in_range_produces_no_issue() -> None:
    spec = LengthSpec(unit="words", target=10, tolerance=3)
    report = length.validate("Una frase de exactamente nueve palabras contadas sin trampa.\n", spec)
    assert report.issues == []


def test_bullets_are_blocking_even_with_right_length() -> None:
    spec = LengthSpec(unit="lines", target=2, tolerance=0)
    report = length.validate("Una frase.\n- otra en viñeta\n", spec, chapter=3)
    assert [issue.code for issue in report.blocking] == ["LEN-FORBIDDEN-FORMAT"]
