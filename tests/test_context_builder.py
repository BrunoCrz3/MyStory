"""T-05: prioridad de recorte de las capas de contexto."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from novela.config import Profile, resolve
from novela.context.builder import build_chapter_context, estimate_tokens
from novela.context.summarizer import literal_tail
from novela.models import (
    CanonFact,
    ChapterSummary,
    Ledger,
    OpenThread,
    Outline,
    StoryBible,
    StyleArtifact,
)


@pytest.fixture
def canon(repo_root: Path) -> tuple[StoryBible, Outline]:
    read = lambda name: json.loads(  # noqa: E731
        (repo_root / "fixtures" / "llm" / f"{name}.json").read_text("utf-8")
    )["json"]
    return StoryBible.model_validate(read("architect")), Outline.model_validate(read("outliner"))


@pytest.fixture
def previous_text(repo_root: Path) -> str:
    """Texto real del capitulo 2: comparte vocabulario con el plan del 3, de modo
    que la capa L5 (recuperacion) produce resultados y puede recortarse."""
    payload = json.loads((repo_root / "fixtures" / "llm" / "writer_ch2.json").read_text("utf-8"))
    return str(payload["text"])


@pytest.fixture
def rich_profile(sandbox: Path) -> Profile:
    """Perfil full: activa memoria media (L3) y recuperacion (L5)."""
    return resolve(
        repo_root=sandbox, flags={"profile": "full"}, environ={}
    ).config.profile_settings()


def _build(
    canon: tuple[StoryBible, Outline], profile: Profile, budget: int, previous: str
) -> object:
    bible, outline = canon
    ledger = Ledger(
        facts=[
            CanonFact(
                id="f_1",
                subject="chr_1",
                predicate="ubicacion",
                value="Pasarela Seis",
                chapter_established=1,
                evidence="bajó a la Pasarela Seis",
            )
        ],
        threads=[
            OpenThread(
                id="th_1",
                question="¿Quién usaba las ventanas de ceguera?",
                opened_chapter=1,
                planned_close_chapter=3,
                importance="principal",
            )
        ],
        entities=bible.entity_names(),
    )
    summaries = [
        ChapterSummary(
            number=number,
            one_line=f"Resumen corto del capítulo {number}.",
            paragraph=f"Párrafo del capítulo {number}. " * 8,
            by_scene=["beat"],
        )
        for number in (1, 2)
    ]
    return build_chapter_context(
        bible=bible,
        plan=outline.chapter(3),
        ledger=ledger,
        summaries=summaries,
        previous_text=previous,
        style_artifacts=[
            StyleArtifact(id="s1", kind="metafora", text="como un hueso viejo", chapter=1),
            StyleArtifact(id="s2", kind="apertura", text="descripcion del entorno", chapter=1),
        ],
        profile=profile,
        budget=budget,
    )


def test_all_layers_present_with_a_generous_budget(
    canon, rich_profile: Profile, previous_text: str
) -> None:
    context = _build(canon, rich_profile, 1_000_000, previous_text)
    assert set(context.keys()) == {"L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7"}  # type: ignore[attr-defined]


def test_l5_is_trimmed_before_l3_and_l3_before_l1(
    canon, rich_profile: Profile, previous_text: str
) -> None:
    full = _build(canon, rich_profile, 1_000_000, previous_text)
    sizes = {layer.key: layer.tokens for layer in full.layers}  # type: ignore[attr-defined]
    total = sum(sizes.values())

    first = _build(canon, rich_profile, total - sizes["L5"], previous_text)
    assert first.dropped == ["L5"]  # type: ignore[attr-defined]

    second = _build(canon, rich_profile, total - sizes["L5"] - sizes["L3"], previous_text)
    assert second.dropped == ["L5", "L3"]  # type: ignore[attr-defined]

    third = _build(canon, rich_profile, 1, previous_text)
    assert third.dropped == ["L5", "L3", "L1"]  # type: ignore[attr-defined]


def test_protected_layers_are_never_trimmed(
    canon, rich_profile: Profile, previous_text: str
) -> None:
    context = _build(canon, rich_profile, 1, previous_text)
    assert {"L0", "L2", "L4", "L6", "L7"} <= set(context.keys())  # type: ignore[attr-defined]
    assert "L1" not in set(context.keys())  # type: ignore[attr-defined]


def test_literal_tail_uses_the_configured_unit(canon, sandbox: Path, previous_text: str) -> None:
    micro = resolve(repo_root=sandbox, environ={}).config.profile_settings()
    context = _build(canon, micro, 1_000_000, previous_text)
    # micro pide las dos ultimas lineas literales del capitulo anterior.
    expected = "\n".join(line for line in previous_text.splitlines() if line.strip())
    assert context.previous_tail == "\n".join(expected.splitlines()[-2:])  # type: ignore[attr-defined]


def test_tail_by_words() -> None:
    text = "Una frase de cinco palabras.\nOtra frase con seis palabras más.\n"
    assert literal_tail(text, "words", 6).startswith("Otra frase")
    assert literal_tail(text, "words", 0) == ""


def test_canon_is_filtered_by_plan_identifiers(
    canon, rich_profile: Profile, previous_text: str
) -> None:
    context = _build(canon, rich_profile, 1_000_000, previous_text)
    body = context.layer("L1").body  # type: ignore[attr-defined]
    # El capitulo 3 tiene POV chr_1 y transcurre en loc_2: chr_2 y loc_1 no entran.
    assert "chr_1" in body
    assert "chr_2" not in body
    assert "loc_1" not in body


def test_system_and_user_and_debug_are_exposed(
    canon, rich_profile: Profile, previous_text: str
) -> None:
    context = _build(canon, rich_profile, 1_000_000, previous_text)
    assert context.system  # type: ignore[attr-defined]
    assert "### Plan del capítulo" in context.user  # type: ignore[attr-defined]
    assert context.debug["L6"] > 0  # type: ignore[attr-defined]


def test_token_estimate_is_monotonic() -> None:
    assert estimate_tokens("a" * 350) == 100
    assert estimate_tokens("") == 0
