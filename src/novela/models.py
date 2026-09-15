"""Contratos de datos del harness (BUILD_SPEC §5).

Todos los modelos usan `extra="forbid"`: una clave inesperada del modelo o de un
fichero de estado falla de forma ruidosa en lugar de colarse en silencio.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

STRICT = ConfigDict(extra="forbid")


# ---------- configuracion ----------
class LengthSpec(BaseModel):
    """Tamaño objetivo de un capitulo, expresado como unidad + valor.

    El sistema nunca asume "palabras": el modo de pruebas mide en lineas.
    """

    model_config = STRICT

    unit: Literal["lines", "words"]
    target: int = Field(gt=0)
    tolerance: int = Field(ge=0)

    def bounds(self) -> tuple[int, int]:
        return (self.target - self.tolerance, self.target + self.tolerance)


# ---------- canon ----------
class Character(BaseModel):
    model_config = STRICT

    id: str
    name: str
    role: str
    want: str
    need: str
    fear: str
    flaw: str
    voice: str
    arc_start: str
    arc_mid: str
    arc_end: str


class SpeculativePremise(BaseModel):
    """La premisa especulativa. Sin limites no hay conflicto: `limits` es obligatorio."""

    model_config = STRICT

    concept: str
    rules: list[str] = Field(min_length=1)
    limits: list[str] = Field(min_length=1)
    cost: str


class Location(BaseModel):
    model_config = STRICT

    id: str
    name: str
    description: str


class StoryBible(BaseModel):
    model_config = STRICT

    logline: str
    theme: str
    characters: list[Character] = Field(min_length=2, max_length=8)
    locations: list[Location] = Field(min_length=1)
    speculative_premise: SpeculativePremise
    timeline_before: list[str]
    glossary: dict[str, str]
    motifs: list[str]

    def character_by_id(self, character_id: str) -> Character | None:
        return next((c for c in self.characters if c.id == character_id), None)

    def entity_names(self) -> list[str]:
        names = [c.name for c in self.characters]
        names.extend(loc.name for loc in self.locations)
        names.extend(self.glossary)
        return names


# ---------- plan ----------
class Scene(BaseModel):
    model_config = STRICT

    id: str
    beats: list[str] = Field(min_length=1)
    new_information: list[str] = Field(min_length=1)


class ChapterPlan(BaseModel):
    model_config = STRICT

    number: int = Field(ge=1)
    working_title: str
    pov_character_id: str
    location_ids: list[str]
    story_time_start: str
    story_time_end: str
    dramatic_function: str
    goal: str
    conflict: str
    outcome: str
    scenes: list[Scene] = Field(min_length=1)
    threads_opened: list[str]
    threads_advanced: list[str]
    threads_closed: list[str]
    world_state_delta: list[str]
    hook: str
    target_length: LengthSpec

    def all_beats(self) -> list[str]:
        return [beat for scene in self.scenes for beat in scene.beats]


class Outline(BaseModel):
    model_config = STRICT

    chapters: list[ChapterPlan]

    def chapter(self, number: int) -> ChapterPlan:
        for plan in self.chapters:
            if plan.number == number:
                return plan
        raise KeyError(f"La escaleta no contiene el capitulo {number}")


# ---------- estado del mundo ----------
class CanonFact(BaseModel):
    model_config = STRICT

    id: str
    subject: str
    predicate: str
    value: str
    chapter_established: int
    status: Literal["vigente", "revocado"] = "vigente"
    revoked_by: str | None = None
    evidence: str = Field(max_length=200)


class OpenThread(BaseModel):
    model_config = STRICT

    id: str
    question: str
    opened_chapter: int
    planned_close_chapter: int
    closed_chapter: int | None = None
    status: Literal["abierto", "cerrado"] = "abierto"
    importance: Literal["principal", "secundario"]


class ChapterSummary(BaseModel):
    model_config = STRICT

    number: int
    one_line: str
    paragraph: str
    by_scene: list[str]


class StyleArtifact(BaseModel):
    model_config = STRICT

    id: str
    kind: Literal["metafora", "imagen", "apertura", "cierre", "muletilla"]
    text: str
    chapter: int


class Ledger(BaseModel):
    """Estado del mundo acumulado. Solo el Archivista lo escribe, via orquestador."""

    model_config = STRICT

    facts: list[CanonFact] = Field(default_factory=list)
    threads: list[OpenThread] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    timeline: list[str] = Field(default_factory=list)

    def current_facts(self) -> list[CanonFact]:
        return [fact for fact in self.facts if fact.status == "vigente"]

    def open_threads(self) -> list[OpenThread]:
        return [thread for thread in self.threads if thread.status == "abierto"]


class ArchivistOutput(BaseModel):
    """Lo que devuelve el Archivista tras leer el capitulo final."""

    model_config = STRICT

    facts: list[CanonFact] = Field(default_factory=list)
    threads: list[OpenThread] = Field(default_factory=list)
    summary: ChapterSummary
    style_artifacts: list[StyleArtifact] = Field(default_factory=list)
    new_entities: list[str] = Field(default_factory=list)


# ---------- capitulo ----------
class ChapterVersion(BaseModel):
    model_config = STRICT

    number: int
    version: int
    title: str
    text: str
    unit_count: int
    origin: Literal["generated", "rewritten", "patched", "polished", "edited"]
    model: str
    temperature: float
    seed: int | None
    prompt_hash: str
    created_at: datetime


# ---------- validacion ----------
class Severity(StrEnum):
    BLOCKING = "blocking"
    MAJOR = "major"
    MINOR = "minor"


class Issue(BaseModel):
    model_config = STRICT

    code: str
    severity: Severity
    message: str
    chapter: int | None = None
    span: str | None = None
    evidence: str | None = None


# ---------- salidas estructuradas de agentes ----------
class IssueList(BaseModel):
    """Envoltorio del Juez: los modelos devuelven objetos, no arrays sueltos."""

    model_config = STRICT

    issues: list[Issue] = Field(default_factory=list)


class GlobalReview(BaseModel):
    """Salida del Revisor global (fase 4)."""

    model_config = STRICT

    novel_title: str
    synopsis: str
    chapter_titles: dict[str, str] = Field(default_factory=dict)
    corrections: list[Issue] = Field(default_factory=list)
    pacing_notes: list[str] = Field(default_factory=list)
