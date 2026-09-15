"""Bucle de capitulo: fase 3 del diagrama (BUILD_SPEC §10.2).

Reglas que este modulo implementa literalmente:

- El parche **revalida**: no cae directo al Estilista, porque un parche puede
  romper otra cosa.
- Tras el Estilista se revalida la longitud: es el fallo mas comun y silencioso.
- `store.commit_chapter` es la unica escritura del estado del mundo, y es atomica.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from novela.agents.archivist import Archivist, Judge
from novela.agents.stylist import Stylist
from novela.agents.writer import Rewriter, Writer
from novela.config import Config
from novela.context.builder import ChapterContext, build_chapter_context
from novela.errors import BudgetExceeded, ValidationEscalation
from novela.models import (
    ArchivistOutput,
    ChapterPlan,
    ChapterVersion,
    Outline,
    StoryBible,
)
from novela.observability.trace import prompt_hash
from novela.orchestrator.states import ChapterState
from novela.store import SQLiteStore
from novela.validators import continuity, length, repetition
from novela.validators.base import ValidationReport, merge
from novela.validators.length import count_units
from novela.validators.repetition import classify_opening, sentence_openers


@dataclass
class ChapterAgents:
    writer: Writer
    rewriter: Rewriter
    stylist: Stylist
    archivist: Archivist
    judge: Judge


@dataclass
class ChapterRunner:
    """Todo lo que el bucle necesita, ya resuelto por el pipeline."""

    config: Config
    store: SQLiteStore
    agents: ChapterAgents
    bible: StoryBible
    outline: Outline
    reports: dict[int, ValidationReport] = field(default_factory=dict)

    # ---------------- presupuesto ----------------
    def check_budget(self) -> None:
        """Corte ANTES de la llamada, nunca despues (§15)."""
        spent = self.agents.writer.context.cost.total()
        limit = self.config.limits.max_cost_usd
        if spent >= limit:
            raise BudgetExceeded(spent, limit)

    # ---------------- corpus acumulado ----------------
    def _previous_texts(self, number: int) -> list[str]:
        texts = []
        for index in range(1, number):
            version = self.store.latest_chapter(index)
            if version is not None:
                texts.append(version.text)
        return texts

    def _opening_history(self, previous: list[str]) -> list[str]:
        return [classify_opening(text) for text in previous]

    def _seen_openers(self, previous: list[str]) -> set[str]:
        return {opener for text in previous for opener in sentence_openers(text) if opener}

    # ---------------- validacion ----------------
    def validate(self, draft: str, plan: ChapterPlan, *, with_judge: bool) -> ValidationReport:
        previous = self._previous_texts(plan.number)
        ledger = self.store.load_ledger()
        judge_issues = None
        if with_judge and self.config.continuity.llm_judge:
            self.check_budget()
            judge_issues = self.agents.judge.run(draft, self.bible, plan)

        return merge(
            repetition.validate(
                draft,
                previous_texts=previous,
                style_artifacts=self.store.load_style_artifacts(),
                opening_history=self._opening_history(previous),
                seen_openers=self._seen_openers(previous),
                cfg=self.config.repetition,
                chapter=plan.number,
            ),
            continuity.validate(
                draft,
                plan=plan,
                previous_plan=self.outline.chapter(plan.number - 1) if plan.number > 1 else None,
                bible=self.bible,
                ledger=ledger,
                cfg=self.config.continuity,
                chapter=plan.number,
                judge_issues=judge_issues,
            ),
            length.validate(draft, plan.target_length, chapter=plan.number),
        )

    # ---------------- bucle ----------------
    def _resolve(self, draft: str, plan: ChapterPlan, context: ChapterContext) -> str:
        """Ciclo reescritura/parche hasta que no queden bloqueantes ni mayores resolubles."""
        limit = self.config.limits.max_rewrite_attempts
        rewrites = patches = 0

        while True:
            report = self.validate(draft, plan, with_judge=True)
            self.reports[plan.number] = report

            if report.blocking:
                rewrites += 1
                if rewrites > limit:
                    self.store.set_chapter_state(plan.number, ChapterState.ESCALATED)
                    raise ValidationEscalation(plan.number, report)
                self.store.set_chapter_state(plan.number, ChapterState.REWRITING)
                self.check_budget()
                draft = self.agents.rewriter.rewrite(draft, report.blocking, context, plan)
                continue

            if report.major and patches < limit:
                patches += 1
                self.store.set_chapter_state(plan.number, ChapterState.PATCHING)
                self.check_budget()
                # El parche revalida: la siguiente vuelta del bucle lo comprueba.
                draft = self.agents.rewriter.patch(draft, report.major, context, plan)
                continue

            return draft

    def _polish(self, draft: str, plan: ChapterPlan, context: ChapterContext) -> str:
        """Pulido y revalidacion de longitud: el Estilista no puede alterar el recuento."""
        self.store.set_chapter_state(plan.number, ChapterState.POLISHING)
        self.check_budget()
        polished = self.agents.stylist.run(draft, context, plan)
        after = length.validate(polished, plan.target_length, chapter=plan.number)
        if after.blocking:
            self.store.set_chapter_state(plan.number, ChapterState.ESCALATED)
            raise ValidationEscalation(plan.number, after)
        return polished

    def run(self, number: int) -> ChapterVersion:
        """Genera, valida, pule, archiva y consolida un capitulo. Estrictamente secuencial."""
        plan = self.outline.chapter(number)
        self.store.set_chapter_state(number, ChapterState.DRAFTING)

        context = build_chapter_context(
            bible=self.bible,
            plan=plan,
            ledger=self.store.load_ledger(),
            summaries=self.store.load_summaries(),
            previous_text=self._previous_text(number),
            style_artifacts=self.store.load_style_artifacts(),
            profile=self.config.profile_settings(),
            budget=self.config.limits.context_token_budget,
        )

        self.check_budget()
        draft = self.agents.writer.run(context, plan)
        self.store.set_chapter_state(number, ChapterState.VALIDATING)
        resolved = self._resolve(draft, plan, context)
        polished = self._polish(resolved, plan, context)

        self.store.set_chapter_state(number, ChapterState.ARCHIVING)
        self.check_budget()
        archived = self.agents.archivist.run(polished, self.bible, self.store.load_ledger(), plan)
        version = self._version(plan, polished, context)
        self.store.commit_chapter(number, version, archived, ChapterState.DONE)
        self._persist_report(number)
        return version

    def _previous_text(self, number: int) -> str | None:
        previous = self.store.latest_chapter(number - 1) if number > 1 else None
        return previous.text if previous else None

    def _version(self, plan: ChapterPlan, text: str, context: ChapterContext) -> ChapterVersion:
        model = self.config.model_for("stylist")
        return ChapterVersion(
            number=plan.number,
            version=1,
            title=plan.working_title,
            text=text,
            unit_count=count_units(text, plan.target_length.unit),
            origin="polished",
            model=model.name,
            temperature=model.temperature,
            seed=self.config.project.seed,
            prompt_hash=prompt_hash(context.system, context.user),
            created_at=datetime.now(UTC),
        )

    def _persist_report(self, number: int) -> None:
        report = self.reports.get(number)
        if report is not None:
            self.store.save_report(f"chapter_{number:02d}", report.model_dump(mode="json"))


__all__ = ["ArchivistOutput", "ChapterAgents", "ChapterRunner"]
