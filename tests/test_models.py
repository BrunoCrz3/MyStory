"""T-02: contratos de datos."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from novela.models import LengthSpec, Scene, SpeculativePremise, StoryBible


def test_premise_without_limits_does_not_validate() -> None:
    with pytest.raises(ValidationError, match="limits"):
        SpeculativePremise(concept="c", rules=["r"], limits=[], cost="coste")


def test_premise_without_rules_does_not_validate() -> None:
    with pytest.raises(ValidationError, match="rules"):
        SpeculativePremise(concept="c", rules=[], limits=["l"], cost="coste")


@pytest.mark.parametrize(
    ("target", "tolerance", "expected"),
    [(4, 0, (4, 4)), (2500, 500, (2000, 3000)), (120, 20, (100, 140))],
)
def test_length_bounds(target: int, tolerance: int, expected: tuple[int, int]) -> None:
    assert LengthSpec(unit="words", target=target, tolerance=tolerance).bounds() == expected


def test_length_rejects_non_positive_target() -> None:
    with pytest.raises(ValidationError):
        LengthSpec(unit="lines", target=0, tolerance=0)


def test_scene_requires_new_information() -> None:
    with pytest.raises(ValidationError, match="new_information"):
        Scene(id="sc_1_1", beats=["b"], new_information=[])


def test_extra_keys_are_forbidden() -> None:
    with pytest.raises(ValidationError, match="extra"):
        LengthSpec.model_validate({"unit": "lines", "target": 4, "tolerance": 0, "unidad": "x"})


def test_bible_requires_at_least_two_characters(repo_bible: StoryBible) -> None:
    payload = repo_bible.model_dump(mode="json")
    payload["characters"] = payload["characters"][:1]
    with pytest.raises(ValidationError, match="characters"):
        StoryBible.model_validate(payload)


@pytest.fixture
def repo_bible() -> StoryBible:
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    payload = json.loads((root / "fixtures" / "llm" / "architect.json").read_text("utf-8"))
    return StoryBible.model_validate(payload["json"])
