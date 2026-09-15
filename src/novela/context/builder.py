"""Constructor de contexto por capas L0–L7 y presupuesto (BUILD_SPEC §8).

Prioridad de recorte: primero L5 (recuperacion), despues L3 (memoria media),
despues L1 (canon filtrado). L0, L2, L4, L6 y L7 NO se recortan nunca: la cola
literal del capitulo anterior es lo que sostiene la continuidad de tono y es lo
primero que se suele sacrificar por error (§26.3).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from novela.config import Profile
from novela.context.retrieval import Retriever
from novela.context.summarizer import literal_tail, mid_summaries, recent_summary
from novela.models import (
    ChapterPlan,
    ChapterSummary,
    Ledger,
    StoryBible,
    StyleArtifact,
)

#: Estimacion de tokens sin dependencias: suficiente para repartir presupuesto.
CHARS_PER_TOKEN = 3.5

#: Orden en que se sacrifican las capas recortables (§8).
TRIM_ORDER: tuple[str, ...] = ("L5", "L3", "L1")
#: Capas que no se recortan jamas.
PROTECTED: frozenset[str] = frozenset({"L0", "L2", "L4", "L6", "L7"})


def estimate_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN)


@dataclass
class Layer:
    key: str
    title: str
    body: str

    @property
    def tokens(self) -> int:
        return estimate_tokens(self.body)

    def render(self) -> str:
        return f"### {self.title}\n\n{self.body}"


@dataclass
class ChapterContext:
    """Contexto ensamblado. Expone `.system`, `.user` y `.debug` (§8)."""

    layers: list[Layer]
    forbidden_openings: list[str] = field(default_factory=list)
    forbidden_phrases: list[str] = field(default_factory=list)
    previous_tail: str = ""
    dropped: list[str] = field(default_factory=list)

    def layer(self, key: str) -> Layer | None:
        return next((item for item in self.layers if item.key == key), None)

    def keys(self) -> list[str]:
        return [item.key for item in self.layers]

    @property
    def system(self) -> str:
        head = self.layer("L0")
        return head.body if head else ""

    @property
    def user(self) -> str:
        return "\n\n".join(item.render() for item in self.layers if item.key != "L0")

    @property
    def debug(self) -> dict[str, int]:
        return {item.key: item.tokens for item in self.layers}


def _filtered_canon(bible: StoryBible, plan: ChapterPlan) -> str:
    """Capa L1: solo las entidades referenciadas POR IDENTIFICADOR en el plan (§8)."""
    referenced = {plan.pov_character_id, *plan.location_ids}
    characters = [
        character.model_dump(mode="json")
        for character in bible.characters
        if character.id in referenced
    ]
    locations = [
        location.model_dump(mode="json")
        for location in bible.locations
        if location.id in referenced
    ]
    payload = {
        "theme": bible.theme,
        "characters": characters,
        "locations": locations,
        "speculative_premise": bible.speculative_premise.model_dump(mode="json"),
        "motifs": bible.motifs,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _world_state(ledger: Ledger, plan: ChapterPlan) -> str:
    """Capa L2: hechos vigentes de las entidades del plan mas los hilos abiertos."""
    referenced = {plan.pov_character_id, *plan.location_ids, "world"}
    facts = [
        f"- {fact.subject}.{fact.predicate} = {fact.value} (cap. {fact.chapter_established})"
        for fact in ledger.current_facts()
        if fact.subject in referenced or fact.subject == "world"
    ]
    threads = [
        f"- {thread.id}: {thread.question} (abierto en el cap. {thread.opened_chapter}, "
        f"cierre previsto en el {thread.planned_close_chapter})"
        for thread in ledger.open_threads()
    ]
    blocks = []
    if facts:
        blocks.append("Hechos vigentes:\n" + "\n".join(facts))
    if threads:
        blocks.append("Hilos abiertos:\n" + "\n".join(threads))
    return "\n\n".join(blocks) or "Sin hechos ni hilos previos: este es el primer capítulo."


def _prohibitions(artifacts: list[StyleArtifact]) -> tuple[str, list[str], list[str]]:
    """Capa L7: aperturas y expresiones ya usadas."""
    openings = [item.text for item in artifacts if item.kind == "apertura"]
    phrases = [item.text for item in artifacts if item.kind != "apertura"]
    lines = []
    if openings:
        lines.append("Tipos de apertura ya usados: " + ", ".join(openings))
    if phrases:
        lines.append("Expresiones e imágenes ya usadas, prohibidas literalmente:")
        lines.extend(f"- «{phrase}»" for phrase in phrases)
    body = "\n".join(lines) or "Todavía no hay expresiones prohibidas: es el primer capítulo."
    return body, openings, phrases


def _trim(layers: list[Layer], budget: int) -> tuple[list[Layer], list[str]]:
    """Recorta en el orden de §8 hasta caber en el presupuesto. Nunca toca las protegidas."""
    dropped: list[str] = []
    kept = list(layers)
    for key in TRIM_ORDER:
        if sum(item.tokens for item in kept) <= budget:
            break
        if key in PROTECTED:
            continue
        before = len(kept)
        kept = [item for item in kept if item.key != key]
        if len(kept) < before:
            dropped.append(key)
    return kept, dropped


def build_chapter_context(
    *,
    bible: StoryBible,
    plan: ChapterPlan,
    ledger: Ledger,
    summaries: list[ChapterSummary],
    previous_text: str | None,
    style_artifacts: list[StyleArtifact],
    profile: Profile,
    budget: int,
) -> ChapterContext:
    """Ensambla las ocho capas y aplica el presupuesto."""
    unit = plan.target_length.unit
    tail = literal_tail(previous_text or "", unit, profile.context.literal_tail_units)
    prohibitions, openings, phrases = _prohibitions(style_artifacts)

    recent = recent_summary(summaries, plan.number - 1)
    l4_body = "\n\n".join(
        part
        for part in (
            f"Resumen del capítulo {plan.number - 1}:\n{recent}" if recent else "",
            f"Cómo terminaba, literal:\n{tail}" if tail else "",
        )
        if part
    ) or "No hay capítulo anterior."

    layers: list[Layer] = [
        Layer("L0", "Rol y restricciones duras", _role_block(plan)),
        Layer("L1", "Canon filtrado", _filtered_canon(bible, plan)),
        Layer("L2", "Estado del mundo e hilos abiertos", _world_state(ledger, plan)),
    ]
    if profile.context.mid_summaries and plan.number > 2:
        body = mid_summaries(summaries, plan.number - 2)
        if body:
            layers.append(Layer("L3", "Memoria media", body))
    layers.append(Layer("L4", "Capítulo anterior", l4_body))

    if profile.context.rag_top_k > 0 and previous_text:
        hits = Retriever([previous_text]).search(plan.goal, profile.context.rag_top_k)
        if hits:
            body = "\n".join(f"- {document[:400]}" for document, _ in hits)
            layers.append(Layer("L5", "Pasajes recuperados", body))

    layers.append(
        Layer("L6", "Plan del capítulo", json.dumps(plan.model_dump(mode="json"), ensure_ascii=False, indent=2))
    )
    layers.append(Layer("L7", "Prohibiciones de estilo", prohibitions))

    kept, dropped = _trim(layers, budget)
    return ChapterContext(
        layers=kept,
        forbidden_openings=openings,
        forbidden_phrases=phrases,
        previous_tail=tail,
        dropped=dropped,
    )


def _role_block(plan: ChapterPlan) -> str:
    return (
        f"Estás escribiendo el capítulo {plan.number} de una novela de ciencia ficción. "
        "El canon vive fuera de tu contexto: lo que no esté en este mensaje, no existe. "
        "No resumas lo ya ocurrido y no contradigas ningún hecho vigente."
    )
