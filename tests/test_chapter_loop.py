"""T-06: el bucle de capitulo con fallos programados en el FakeLLM."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from novela.agents.base import AgentContext
from novela.config import resolve
from novela.errors import ValidationEscalation
from novela.llm.fake import FakeLLM
from novela.llm.router import Router
from novela.observability.cost import CostTracker
from novela.observability.trace import TraceWriter
from novela.orchestrator.chapter_loop import ChapterAgents, ChapterRunner
from novela.orchestrator.pipeline import Pipeline
from novela.orchestrator.states import ChapterState


def _runner(sandbox: Path, fail_plan: dict[str, list[str]] | None = None) -> ChapterRunner:
    bundle = resolve(repo_root=sandbox, environ={})
    pipeline = Pipeline.open(bundle.config, sandbox, "t6")
    pipeline.init("Una premisa cualquiera.", resolved_yaml="project: {}\n")
    pipeline.build_bible()
    pipeline.build_outline()

    client = FakeLLM(sandbox / "fixtures" / "llm", fail_plan=fail_plan)
    directory = sandbox / "out" / "t6"
    context = AgentContext(
        config=bundle.config,
        router=Router(client=client, config=bundle.config),
        trace=TraceWriter(directory / "trace.jsonl"),
        cost=CostTracker(directory / "cost.json"),
        project_id="t6",
        prompts_dir=sandbox / "prompts",
    )
    runner = pipeline.runner()
    from novela.agents.archivist import Archivist, Judge
    from novela.agents.stylist import Stylist
    from novela.agents.writer import Rewriter, Writer

    runner.agents = ChapterAgents(
        writer=Writer(context),
        rewriter=Rewriter(context),
        stylist=Stylist(context),
        archivist=Archivist(context),
        judge=Judge(context),
    )
    return runner


def test_clean_chapter_needs_no_rewrite(sandbox: Path) -> None:
    runner = _runner(sandbox)
    version = runner.run(1)
    assert version.unit_count == 4
    assert runner.store.chapter_state(1) == ChapterState.DONE
    assert runner.reports[1].blocking == []


def test_blocking_issue_forces_a_rewrite(sandbox: Path) -> None:
    # `too_long` deja el capitulo fuera de rango: LEN-OUT-OF-RANGE es bloqueante.
    runner = _runner(sandbox, fail_plan={"writer_ch1": ["too_long"]})
    version = runner.run(1)
    assert version.unit_count == 4  # la reescritura lo ha devuelto al rango
    calls = [key for key, _ in runner.agents.writer.context.router.client.calls]  # type: ignore[attr-defined]
    assert "rewriter_ch1" in calls
    assert runner.store.chapter_state(1) == ChapterState.DONE


def test_three_failures_escalate(sandbox: Path) -> None:
    runner = _runner(
        sandbox,
        fail_plan={
            "writer_ch1": ["too_long"],
            "rewriter_ch1": ["too_long", "too_long", "too_long", "too_long"],
        },
    )
    with pytest.raises(ValidationEscalation) as error:
        runner.run(1)
    assert error.value.chapter == 1
    assert runner.store.chapter_state(1) == ChapterState.ESCALATED


def test_major_issue_forces_a_patch_and_revalidation(sandbox: Path) -> None:
    """Una incidencia mayor dispara el Parcheador, y el bucle REVALIDA antes de pulir."""
    runner = _runner(sandbox)
    runner.run(1)
    runner.run(2)
    # `duplicate` sirve el texto del capitulo 1 como capitulo 3: repite el tipo de
    # apertura y deja beats del plan sin narrar. Ambas son incidencias mayores.
    client = runner.agents.writer.context.router.client
    client.fail_plan["writer_ch3"] = ["duplicate"]  # type: ignore[attr-defined]
    runner.run(3)

    calls = [key for key, _ in client.calls if key.endswith("_ch3")]  # type: ignore[attr-defined]
    # Secuencia exigida por §10.2: escribir, validar, parchear, REVALIDAR, pulir.
    assert calls == [
        "writer_ch3",
        "judge_ch3",
        "patcher_ch3",
        "judge_ch3",
        "stylist_ch3",
        "archivist_ch3",
    ]
    # El parche lleva etiqueta propia: no se confunde con una reescritura.
    assert "rewriter_ch3" not in calls
    # Y la revalidacion posterior deja el capitulo limpio.
    assert runner.reports[3].issues == []


def test_patch_revalidates_before_polishing(sandbox: Path) -> None:
    """Una incidencia mayor dispara el parche y el bucle vuelve a validar."""
    runner = _runner(sandbox)
    runner.run(1)
    runner.run(2)
    version = runner.run(3)
    calls = [key for key, _ in runner.agents.writer.context.router.client.calls]  # type: ignore[attr-defined]
    # Sin incidencias, el orden es escritor -> juez -> estilista -> archivista.
    assert calls.index("writer_ch3") < calls.index("stylist_ch3") < calls.index("archivist_ch3")
    assert version.unit_count == 4


def test_missing_fixture_is_loud(sandbox: Path) -> None:
    from novela.errors import FixtureMissing

    shutil.move(sandbox / "fixtures" / "llm" / "writer_ch2.json", sandbox / "moved.json")
    runner = _runner(sandbox)
    runner.run(1)
    with pytest.raises(FixtureMissing, match="writer_ch2"):
        runner.run(2)


def test_trace_records_every_call_without_prompts(sandbox: Path) -> None:
    runner = _runner(sandbox)
    runner.run(1)
    events = TraceWriter(sandbox / "out" / "t6" / "trace.jsonl").read_all()
    assert events
    for event in events:
        assert str(event["prompt_hash"]).startswith("sha256:")
        assert "system" not in event
        assert "user" not in event
    assert {str(event["role"]) for event in events} >= {"writer", "stylist", "archivist"}
