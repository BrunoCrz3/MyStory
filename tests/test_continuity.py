"""T-04: muertos que actuan, cronologia invertida y reglas violadas."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from novela.config import resolve
from novela.models import CanonFact, ChapterPlan, Ledger, Outline, StoryBible
from novela.validators import continuity


@pytest.fixture
def bible(repo_root: Path) -> StoryBible:
    payload = json.loads((repo_root / "fixtures" / "llm" / "architect.json").read_text("utf-8"))
    return StoryBible.model_validate(payload["json"])


@pytest.fixture
def outline(repo_root: Path) -> Outline:
    payload = json.loads((repo_root / "fixtures" / "llm" / "outliner.json").read_text("utf-8"))
    return Outline.model_validate(payload["json"])


def _cfg(sandbox: Path) -> object:
    return resolve(repo_root=sandbox, environ={}).config.continuity


def _validate(
    text: str,
    plan: ChapterPlan,
    bible: StoryBible,
    sandbox: Path,
    *,
    ledger: Ledger | None = None,
    previous: ChapterPlan | None = None,
) -> object:
    return continuity.validate(
        text,
        plan=plan,
        previous_plan=previous,
        bible=bible,
        ledger=ledger or Ledger(entities=bible.entity_names()),
        cfg=_cfg(sandbox),  # type: ignore[arg-type]
        chapter=plan.number,
    )


def test_dead_character_acting_is_blocking(
    bible: StoryBible, outline: Outline, sandbox: Path
) -> None:
    ledger = Ledger(
        facts=[
            CanonFact(
                id="f_dead",
                subject="chr_2",
                predicate="estado_vital",
                value="muerto",
                chapter_established=1,
                evidence="Teo dejó de respirar en la esclusa",
            )
        ],
        entities=bible.entity_names(),
    )
    text = "Teo enumeró la cuota, los plazos y el precio de una concesión perdida.\n"
    report = _validate(text, outline.chapter(3), bible, sandbox, ledger=ledger)
    assert "CONT-DEAD-ACTS" in {issue.code for issue in report.blocking}  # type: ignore[attr-defined]
    assert report.metrics["cont.dead_acting"] == 1.0  # type: ignore[attr-defined]


def test_inverted_timeline_is_blocking(bible: StoryBible, outline: Outline, sandbox: Path) -> None:
    later = outline.chapter(3)
    inverted = later.model_copy(update={"story_time_start": "turno 410, hora 01:00"})
    report = _validate(
        "Una frase cualquiera.\n", inverted, bible, sandbox, previous=outline.chapter(2)
    )
    assert "CONT-TIMELINE" in {issue.code for issue in report.blocking}  # type: ignore[attr-defined]


def test_declared_flashback_does_not_trigger_timeline(
    bible: StoryBible, outline: Outline, sandbox: Path
) -> None:
    flashback = outline.chapter(3).model_copy(
        update={"story_time_start": "turno 410, hora 01:00", "dramatic_function": "flashback"}
    )
    report = _validate(
        "Una frase cualquiera.\n", flashback, bible, sandbox, previous=outline.chapter(2)
    )
    assert "CONT-TIMELINE" not in {issue.code for issue in report.issues}  # type: ignore[attr-defined]


def test_violated_world_rule_is_blocking(
    bible: StoryBible, outline: Outline, sandbox: Path
) -> None:
    limit = bible.speculative_premise.limits[1]
    assert "casco presurizado" in limit
    text = "El sistema mostró con nitidez lo que sucede fuera del casco presurizado.\n"
    report = _validate(text, outline.chapter(1), bible, sandbox)
    assert "CONT-RULE-VIOLATION" in {issue.code for issue in report.blocking}  # type: ignore[attr-defined]


def test_name_drift_is_major(bible: StoryBible, outline: Outline, sandbox: Path) -> None:
    text = "Nadya revisó el sello del guante izquierdo antes de bajar.\n"
    report = _validate(text, outline.chapter(1), bible, sandbox)
    assert "CONT-NAME-DRIFT" in {issue.code for issue in report.major}  # type: ignore[attr-defined]


def test_canonical_spelling_does_not_drift(
    bible: StoryBible, outline: Outline, sandbox: Path
) -> None:
    text = "Nadia revisó el sello del guante izquierdo antes de bajar.\n"
    report = _validate(text, outline.chapter(1), bible, sandbox)
    assert report.metrics["cont.name_drift"] == 0.0  # type: ignore[attr-defined]


def test_conflicting_current_facts_are_blocking(
    bible: StoryBible, outline: Outline, sandbox: Path
) -> None:
    ledger = Ledger(
        facts=[
            CanonFact(
                id="a",
                subject="chr_1",
                predicate="ubicacion",
                value="Pasarela Seis",
                chapter_established=1,
                evidence="bajó a la Pasarela Seis",
            ),
            CanonFact(
                id="b",
                subject="chr_1",
                predicate="ubicacion",
                value="Sala del Oráculo",
                chapter_established=2,
                evidence="entró en la sala",
            ),
        ],
        entities=bible.entity_names(),
    )
    report = _validate("Una frase.\n", outline.chapter(2), bible, sandbox, ledger=ledger)
    assert "CONT-FACT-CONFLICT" in {issue.code for issue in report.blocking}  # type: ignore[attr-defined]


def test_revoked_fact_does_not_conflict(bible: StoryBible, outline: Outline, sandbox: Path) -> None:
    ledger = Ledger(
        facts=[
            CanonFact(
                id="a",
                subject="chr_1",
                predicate="ubicacion",
                value="Pasarela Seis",
                chapter_established=1,
                status="revocado",
                revoked_by="b",
                evidence="bajó a la Pasarela Seis",
            ),
            CanonFact(
                id="b",
                subject="chr_1",
                predicate="ubicacion",
                value="Sala del Oráculo",
                chapter_established=2,
                evidence="entró en la sala",
            ),
        ],
        entities=bible.entity_names(),
    )
    report = _validate("Una frase.\n", outline.chapter(2), bible, sandbox, ledger=ledger)
    assert report.metrics["cont.fact_conflicts"] == 0.0  # type: ignore[attr-defined]


def test_overlapping_intervals_in_two_places_is_blocking(
    bible: StoryBible, outline: Outline, sandbox: Path
) -> None:
    previous = outline.chapter(1)  # loc_1, termina en el turno 412 hora 09:20
    overlapping = outline.chapter(2).model_copy(
        update={"story_time_start": "turno 412, hora 07:00", "dramatic_function": "flashback"}
    )
    report = _validate("Una frase.\n", overlapping, bible, sandbox, previous=previous)
    assert "CONT-LOCATION-IMPOSSIBLE" in {issue.code for issue in report.blocking}  # type: ignore[attr-defined]


def test_missing_beats_are_major(bible: StoryBible, outline: Outline, sandbox: Path) -> None:
    report = _validate(
        "Llovía sobre el tejado de zinc de la casa vacía.\n", outline.chapter(1), bible, sandbox
    )
    assert "CONT-BEAT-MISSING" in {issue.code for issue in report.major}  # type: ignore[attr-defined]
    assert report.metrics["cont.beat_coverage"] < 0.8  # type: ignore[attr-defined]


def test_judge_issues_are_merged(bible: StoryBible, outline: Outline, sandbox: Path) -> None:
    from novela.models import Issue, Severity

    judged = [Issue(code="CONT-VOICE-DRIFT", severity=Severity.MAJOR, message="voz", chapter=1)]
    report = continuity.validate(
        "Una frase.\n",
        plan=outline.chapter(1),
        previous_plan=None,
        bible=bible,
        ledger=Ledger(entities=bible.entity_names()),
        cfg=_cfg(sandbox),  # type: ignore[arg-type]
        chapter=1,
        judge_issues=judged,
    )
    assert "CONT-VOICE-DRIFT" in {issue.code for issue in report.major}
    assert report.metrics["cont.judge_issues"] == 1.0
