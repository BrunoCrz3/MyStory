"""Pipeline de las fases 0–5 (BUILD_SPEC §10.3).

Los puntos de control respetan `approval.*`: en `auto` continuan tras validar; en
`manual` dejan el proyecto en estado `*_REVIEW` y devuelven el control a la CLI.
El corte por presupuesto ocurre ANTES de cada llamada, nunca despues.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from novela.agents.architect import Architect
from novela.agents.archivist import Archivist, Judge
from novela.agents.base import AgentContext
from novela.agents.outliner import Outliner
from novela.agents.reviewer import Reviewer
from novela.agents.stylist import Stylist
from novela.agents.writer import Rewriter, Writer
from novela.config import Config, project_dir
from novela.errors import NovelaError, StoreError
from novela.export.assembler import assemble, write_manuscript
from novela.export.pdf import export_pdf
from novela.llm.router import Router, build_client
from novela.models import GlobalReview, Outline, StoryBible
from novela.observability.cost import CostTracker
from novela.observability.trace import TraceWriter
from novela.orchestrator.chapter_loop import ChapterAgents, ChapterRunner
from novela.orchestrator.states import ChapterState, ProjectState
from novela.store import SQLiteStore
from novela.validators import bible as bible_validator
from novela.validators import outline as outline_validator
from novela.validators.base import ValidationReport


@dataclass
class Pipeline:
    """Fases 0–5 sobre un proyecto ya creado en disco."""

    config: Config
    repo_root: Path
    project_id: str
    store: SQLiteStore
    agents_context: AgentContext

    @classmethod
    def open(cls, config: Config, repo_root: Path, project_id: str) -> Pipeline:
        directory = project_dir(repo_root, project_id)
        store = SQLiteStore(project_id, directory)
        client = build_client(config, fixtures_dir=repo_root / "fixtures" / "llm")
        context = AgentContext(
            config=config,
            router=Router(client=client, config=config),
            trace=TraceWriter(directory / "trace.jsonl"),
            cost=CostTracker(directory / "cost.json"),
            project_id=project_id,
            prompts_dir=repo_root / "prompts",
        )
        return cls(config, repo_root, project_id, store, context)

    @property
    def directory(self) -> Path:
        return project_dir(self.repo_root, self.project_id)

    # ---------------- fase 0 ----------------
    def init(self, premise: str, *, resolved_yaml: str) -> None:
        self.store.create_project(premise, ProjectState.DRAFT)
        (self.directory / "config.snapshot.yaml").write_text(resolved_yaml, encoding="utf-8")
        project_config = self.directory / "config.yaml"
        if not project_config.exists():
            project_config.write_text(
                "# Configuración de este proyecto. Editable a mitad de obra (§3.8).\n"
                "# Lo que no aparezca aquí se hereda de novela.yaml y config/default.yaml.\n",
                encoding="utf-8",
            )

    def log_config_change(self, key: str, old: object, new: object) -> None:
        from datetime import UTC, datetime

        entry = {
            "ts": datetime.now(UTC).isoformat(),
            "key": key,
            "old": old,
            "new": new,
        }
        with (self.directory / "config.changelog.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ---------------- fase 1 ----------------
    def build_bible(self, *, regenerate: bool = False) -> tuple[StoryBible, ValidationReport]:
        existing = self.store.load_bible()
        if existing is not None and not regenerate:
            return existing, bible_validator.validate(existing)

        self.store.set_project_state(ProjectState.BIBLE_GENERATING)
        self._check_budget()
        bible = Architect(self.agents_context).run(self.store.premise())
        report = bible_validator.validate(bible)
        self.store.save_bible(bible)
        self.store.save_report("bible_validation", report.model_dump(mode="json"))
        self.store.set_project_state(
            ProjectState.BIBLE_APPROVED
            if self.config.approval.bible == "auto" and not report.blocking
            else ProjectState.BIBLE_REVIEW
        )
        return bible, report

    # ---------------- fase 2 ----------------
    def build_outline(self, *, regenerate: bool = False) -> tuple[Outline, ValidationReport]:
        bible = self._require_bible()
        existing = self.store.load_outline()
        if existing is not None and not regenerate:
            return existing, outline_validator.validate(
                existing, expected_chapters=self.config.novel.chapters
            )

        self.store.set_project_state(ProjectState.OUTLINE_GENERATING)
        self._check_budget()
        outline = Outliner(self.agents_context).run(bible)
        report = outline_validator.validate(
            outline, expected_chapters=self.config.novel.chapters
        )
        report.issues.extend(bible_validator.validate(bible, outline=outline).issues)
        self.store.save_outline(outline)
        self.store.save_report("outline_validation", report.model_dump(mode="json"))
        self.store.set_project_state(
            ProjectState.OUTLINE_APPROVED
            if self.config.approval.outline == "auto" and not report.blocking
            else ProjectState.OUTLINE_REVIEW
        )
        return outline, report

    # ---------------- fase 3 ----------------
    def runner(self) -> ChapterRunner:
        return ChapterRunner(
            config=self.config,
            store=self.store,
            agents=ChapterAgents(
                writer=Writer(self.agents_context),
                rewriter=Rewriter(self.agents_context),
                stylist=Stylist(self.agents_context),
                archivist=Archivist(self.agents_context),
                judge=Judge(self.agents_context),
            ),
            bible=self._require_bible(),
            outline=self._require_outline(),
        )

    def write_chapters(self, first: int, last: int) -> list[int]:
        """Capitulos estrictamente secuenciales: el i depende del mundo tras el i-1."""
        self.store.set_project_state(ProjectState.WRITING)
        runner = self.runner()
        written: list[int] = []
        for number in range(first, last + 1):
            if self.store.chapter_state(number) == ChapterState.DONE:
                continue
            runner.run(number)
            written.append(number)
        self.agents_context.cost.flush()
        return written

    # ---------------- fase 4 ----------------
    def review(self) -> GlobalReview:
        self.store.set_project_state(ProjectState.GLOBAL_REVIEW)
        bible = self._require_bible()
        chapters = self.store.all_chapters()
        draft = assemble(title=bible.logline[:60], logline=bible.logline, chapters=chapters)
        self._check_budget()
        result = Reviewer(self.agents_context).run(
            draft, bible, self.store.load_ledger(), self.store.load_summaries()
        )
        self._write_review_reports(result)
        return result

    def _write_review_reports(self, result: GlobalReview) -> None:
        ledger = self.store.load_ledger()
        self.store.save_report(
            "continuity",
            {
                "facts_vigentes": len(ledger.current_facts()),
                "hilos_abiertos": [thread.id for thread in ledger.open_threads()],
                "cronologia": ledger.timeline,
                "entidades": ledger.entities,
            },
        )
        self.store.save_report(
            "repetition",
            {
                f"chapter_{number:02d}": report.metrics
                for number, report in sorted(self._chapter_metrics().items())
            },
        )
        self.store.save_report(
            "pacing",
            {
                "notas": result.pacing_notes,
                "longitudes": {
                    f"chapter_{chapter.number:02d}": chapter.unit_count
                    for chapter in self.store.all_chapters()
                },
            },
        )
        self.store.save_report(
            "corrections", [issue.model_dump(mode="json") for issue in result.corrections]
        )
        self.store.save_report("bible", self._require_bible().model_dump(mode="json"))
        self.store.save_report("outline", self._require_outline().model_dump(mode="json"))
        self.store.save_report("ledger", ledger.model_dump(mode="json"))

    def _chapter_metrics(self) -> dict[int, ValidationReport]:
        metrics: dict[int, ValidationReport] = {}
        for path in sorted((self.directory / "reports").glob("chapter_*.json")):
            number = int(path.stem.split("_")[1])
            metrics[number] = ValidationReport.model_validate(
                json.loads(path.read_text(encoding="utf-8"))
            )
        return metrics

    # ---------------- fase 5 ----------------
    def export(self, formats: list[str], review: GlobalReview | None = None) -> dict[str, Path]:
        bible = self._require_bible()
        chapters = self.store.all_chapters()
        title = review.novel_title if review else bible.logline[:60]
        titles = review.chapter_titles if review else None
        content = assemble(title=title, logline=bible.logline, chapters=chapters, titles=titles)

        produced: dict[str, Path] = {}
        if "md" in formats:
            produced["md"] = write_manuscript(self.directory / "manuscrito.md", content)
        if "pdf" in formats:
            markdown = produced.get("md") or write_manuscript(
                self.directory / "manuscrito.md", content
            )
            result = export_pdf(markdown, self.directory / "manuscrito.pdf")
            if result.path is not None:
                produced["pdf"] = result.path
        self.store.set_project_state(ProjectState.COMPLETED)
        self.agents_context.cost.flush()
        return produced

    # ---------------- utilidades ----------------
    def run_auto(self) -> dict[str, Path]:
        """Fases 1 -> 5 sin intervencion (`novela run <pid> --auto`)."""
        self.build_bible()
        self.build_outline()
        self.write_chapters(1, self.config.novel.chapters)
        review = self.review()
        return self.export(["md", "pdf"], review)

    def _check_budget(self) -> None:
        from novela.errors import BudgetExceeded

        spent = self.agents_context.cost.total()
        if spent >= self.config.limits.max_cost_usd:
            raise BudgetExceeded(spent, self.config.limits.max_cost_usd)

    def _require_bible(self) -> StoryBible:
        bible = self.store.load_bible()
        if bible is None:
            raise StoreError(
                f"el proyecto '{self.project_id}' no tiene biblia. Ejecuta `novela bible "
                f"{self.project_id}` antes de continuar."
            )
        return bible

    def _require_outline(self) -> Outline:
        outline = self.store.load_outline()
        if outline is None:
            raise StoreError(
                f"el proyecto '{self.project_id}' no tiene escaleta. Ejecuta `novela outline "
                f"{self.project_id}` antes de continuar."
            )
        return outline


__all__ = ["NovelaError", "Pipeline"]
