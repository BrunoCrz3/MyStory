"""T-03: la misma metrica, distinta severidad segun perfil."""

from __future__ import annotations

from pathlib import Path

from novela.config import resolve
from novela.models import StyleArtifact
from novela.validators import repetition

ALMOST_IDENTICAL_A = (
    "El hielo de Encélado crujía bajo la rejilla como un hueso viejo.\n"
    "Nadia revisó el sello del guante y anotó la microfuga del turno.\n"
)
ALMOST_IDENTICAL_B = (
    "El hielo de Encélado crujía bajo la rejilla como un hueso antiguo.\n"
    "Nadia revisó el sello del guante y anotó la microfuga del turno.\n"
)


def _run(text: str, previous: list[str], profile: str, sandbox: Path) -> object:
    cfg = resolve(repo_root=sandbox, flags={"profile": profile}, environ={}).config.repetition
    return repetition.validate(
        text,
        previous_texts=previous,
        style_artifacts=[],
        opening_history=[],
        seen_openers=set(),
        cfg=cfg,
        chapter=2,
    )


def test_near_duplicate_blocks_in_full_but_not_in_micro(sandbox: Path) -> None:
    full_cfg_blocking = resolve(
        repo_root=sandbox, flags={"profile": "full"}, environ={}
    ).config.repetition.jaccard_blocking
    assert full_cfg_blocking is not None
    full = _run(ALMOST_IDENTICAL_B, [ALMOST_IDENTICAL_A], "full", sandbox)
    micro = _run(ALMOST_IDENTICAL_B, [ALMOST_IDENTICAL_A], "micro", sandbox)

    assert "REP-NGRAM" in {issue.code for issue in full.blocking}  # type: ignore[attr-defined]
    assert "REP-NGRAM" not in {issue.code for issue in micro.blocking}  # type: ignore[attr-defined]

    # La metrica se registra en AMBOS perfiles: es lo que permite calibrar despues.
    # El jaccard difiere porque cada perfil usa su propio `ngram_size`; el coseno no.
    assert full.metrics["rep.jaccard_max"] > full_cfg_blocking  # type: ignore[attr-defined]
    assert micro.metrics["rep.jaccard_max"] > 0.0  # type: ignore[attr-defined]
    assert micro.metrics["rep.cosine_max"] == full.metrics["rep.cosine_max"]  # type: ignore[attr-defined]


def test_distinct_chapters_do_not_trigger_anything(sandbox: Path) -> None:
    other = "Teo enumeró la cuota trimestral, los plazos y el precio de la concesión.\n"
    report = _run(other, [ALMOST_IDENTICAL_A], "full", sandbox)
    assert report.blocking == []  # type: ignore[attr-defined]


def test_opening_types_are_classified_by_rules() -> None:
    assert repetition.classify_opening("—Consulta el Oráculo —dijo Teo.\n") == "dialogo"
    assert repetition.classify_opening("Arrancó el panel del mamparo.\n") == "accion"
    assert repetition.classify_opening("El hielo crujía bajo la rejilla.\n") == "descripcion"
    assert repetition.classify_opening("Nadia recordó el invierno anterior.\n") == "reflexion"


def test_repeated_opening_type_is_major(sandbox: Path) -> None:
    cfg = resolve(repo_root=sandbox, environ={}).config.repetition
    report = repetition.validate(
        "—Otra vez el mismo arranque —dijo alguien.\n",
        previous_texts=[],
        style_artifacts=[],
        opening_history=["dialogo"],
        seen_openers=set(),
        cfg=cfg,
        chapter=2,
    )
    assert "REP-OPENING-TYPE" in {issue.code for issue in report.major}


def test_reused_sentence_opener_is_minor(sandbox: Path) -> None:
    cfg = resolve(repo_root=sandbox, environ={}).config.repetition
    report = repetition.validate(
        "Nadia revisó el sello del guante.\n",
        previous_texts=[],
        style_artifacts=[],
        opening_history=[],
        seen_openers={"nadia reviso el"},
        cfg=cfg,
        chapter=2,
    )
    assert "REP-SENTENCE-OPENER" in {issue.code for issue in report.minor}


def test_image_reuse_is_major(sandbox: Path) -> None:
    cfg = resolve(repo_root=sandbox, environ={}).config.repetition
    artifact = StyleArtifact(
        id="sty_1_a", kind="metafora", text="como un hueso que se acomoda", chapter=1
    )
    # El umbral de §9.4 es estricto (> 0,90): solo salta la reutilizacion casi literal.
    report = repetition.validate(
        "Como un hueso que se acomoda.\n",
        previous_texts=[],
        style_artifacts=[artifact],
        opening_history=[],
        seen_openers=set(),
        cfg=cfg,
        chapter=2,
    )
    assert "REP-IMAGE-REUSE" in {issue.code for issue in report.major}


def test_mtld_is_always_recorded(sandbox: Path) -> None:
    report = _run(ALMOST_IDENTICAL_A, [], "micro", sandbox)
    assert "rep.mtld" in report.metrics  # type: ignore[attr-defined]
