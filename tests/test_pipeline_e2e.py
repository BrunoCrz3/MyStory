"""T-07 y T-08: la demo completa, offline, y el ledger resultante."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

from novela.config import resolve
from novela.orchestrator.pipeline import Pipeline
from novela.orchestrator.states import ProjectState
from novela.validators.length import count_units

CHAPTER_RE = re.compile(r"^## Capítulo (\d+) — (.+)$", re.MULTILINE)


@pytest.fixture
def demo(sandbox: Path) -> Pipeline:
    bundle = resolve(repo_root=sandbox, flags={"llm.provider": "fake"}, environ={})
    pipeline = Pipeline.open(bundle.config, sandbox, "demo")
    pipeline.init("Una premisa de prueba.", resolved_yaml="project: {}\n")
    return pipeline


# ---------------------------------------------------------------- T-07
def test_demo_produces_three_chapters_of_four_lines(demo: Pipeline, sandbox: Path) -> None:
    started = time.monotonic()
    produced = demo.run_auto()
    elapsed = time.monotonic() - started

    assert elapsed < 10.0, f"la demo ha tardado {elapsed:.1f}s y el límite son 10s"
    markdown = produced["md"].read_text(encoding="utf-8")
    chapters = CHAPTER_RE.split(markdown)[1:]
    numbers = [int(chapters[index]) for index in range(0, len(chapters), 3)]
    assert numbers == [1, 2, 3]

    bodies = [chapters[index + 2] for index in range(0, len(chapters), 3)]
    assert [count_units(body, "lines") for body in bodies] == [4, 4, 4]
    assert demo.store.project_state() == ProjectState.COMPLETED


def test_demo_needs_no_network_and_no_api_key(
    demo: Pipeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    import socket

    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("el pipeline ha intentado abrir una conexión de red")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    demo.run_auto()


def test_demo_writes_every_runtime_output_of_the_spec(demo: Pipeline) -> None:
    demo.run_auto()
    directory = demo.directory
    for name in (
        "project.db",
        "config.snapshot.yaml",
        "config.yaml",
        "bible.json",
        "outline.json",
        "ledger.json",
        "summaries.json",
        "style_artifacts.json",
        "manuscrito.md",
        "trace.jsonl",
        "cost.json",
    ):
        assert (directory / name).is_file(), f"falta out/demo/{name}"
    for number in (1, 2, 3):
        assert (directory / "chapters" / f"ch_{number:02d}.md").is_file()
        assert (directory / "chapters" / f"ch_{number:02d}.versions.json").is_file()
    for report in ("continuity", "repetition", "pacing", "corrections", "ledger"):
        assert (directory / "reports" / f"{report}.json").is_file()


# ---------------------------------------------------------------- T-08
def test_ledger_has_facts_per_chapter_and_no_open_threads(demo: Pipeline) -> None:
    demo.run_auto()
    ledger = json.loads((demo.directory / "ledger.json").read_text(encoding="utf-8"))

    for number in (1, 2, 3):
        established = [f for f in ledger["facts"] if f["chapter_established"] == number]
        assert established, f"el capítulo {number} no aporta ningún CanonFact"

    assert [t for t in ledger["threads"] if t["status"] == "abierto"] == []


def test_revoked_facts_are_kept_not_deleted(demo: Pipeline) -> None:
    demo.run_auto()
    ledger = json.loads((demo.directory / "ledger.json").read_text(encoding="utf-8"))
    revoked = [fact for fact in ledger["facts"] if fact["status"] == "revocado"]
    assert revoked, "los hechos se revocan, no se borran"
    assert all(fact["revoked_by"] for fact in revoked)


def test_resuming_does_not_repeat_finished_chapters(demo: Pipeline) -> None:
    demo.build_bible()
    demo.build_outline()
    assert demo.write_chapters(1, 3) == [1, 2, 3]
    # Segunda pasada: todo estaba hecho, no se reescribe nada.
    assert demo.write_chapters(1, 3) == []


def test_cli_demo_command_runs_offline(repo_root: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "novela", "demo"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert (repo_root / "out" / "demo" / "manuscrito.md").is_file()


# ---------------------------------------------------------------- CLI
def test_cli_full_flow(cli_in: Path) -> None:
    """init -> bible -> outline -> write -> review -> export -> status -> cost."""
    from typer.testing import CliRunner

    from novela.cli import app

    runner = CliRunner()
    assert runner.invoke(app, ["init", "Una premisa.", "--project-id", "c1"]).exit_code == 0
    assert runner.invoke(app, ["bible", "c1", "--approve"]).exit_code == 0
    assert runner.invoke(app, ["outline", "c1", "--approve"]).exit_code == 0
    assert runner.invoke(app, ["write", "c1"]).exit_code == 0
    assert runner.invoke(app, ["review", "c1"]).exit_code == 0
    assert runner.invoke(app, ["export", "c1", "--format", "md,pdf"]).exit_code == 0

    status_result = runner.invoke(app, ["status", "c1"])
    assert status_result.exit_code == 0
    assert "done" in status_result.stdout

    continuity_result = runner.invoke(app, ["continuity", "c1"])
    assert continuity_result.exit_code == 0
    assert "Sin hilos abiertos" in continuity_result.stdout

    assert runner.invoke(app, ["cost", "c1"]).exit_code == 0
    assert (cli_in / "out" / "c1" / "manuscrito.md").is_file()


def test_cli_run_auto(cli_in: Path) -> None:
    from typer.testing import CliRunner

    from novela.cli import app

    runner = CliRunner()
    runner.invoke(app, ["init", "Una premisa.", "--project-id", "c2", "--chapters", "3"])
    # Sin --auto la CLI se niega a ejecutar el pipeline entero.
    assert runner.invoke(app, ["run", "c2"]).exit_code == 1
    assert runner.invoke(app, ["run", "c2", "--auto"]).exit_code == 0
    assert (cli_in / "out" / "c2" / "manuscrito.pdf").is_file()


def test_cli_config_commands(cli_in: Path) -> None:
    from typer.testing import CliRunner

    from novela.cli import app

    runner = CliRunner()
    assert runner.invoke(app, ["config", "init"]).exit_code == 0
    assert (cli_in / "novela.yaml").is_file()
    # Idempotente: no sobrescribe el fichero del usuario.
    assert runner.invoke(app, ["config", "init"]).exit_code == 0

    assert runner.invoke(app, ["config", "validate"]).exit_code == 0
    assert runner.invoke(app, ["config", "set", "novel.chapters", "6"]).exit_code == 0
    assert "6" in runner.invoke(app, ["config", "get", "novel.chapters"]).stdout

    shown = runner.invoke(app, ["config", "show", "--resolved"])
    assert shown.exit_code == 0
    assert "novela.yaml" in shown.stdout

    assert runner.invoke(app, ["config", "show"]).exit_code == 0


def test_cli_config_validate_fails_loudly(cli_in: Path) -> None:
    from typer.testing import CliRunner

    from novela.cli import app

    (cli_in / "novela.yaml").write_text("novel:\n  chapter: 5\n", encoding="utf-8")
    result = CliRunner().invoke(app, ["config", "validate"])
    assert result.exit_code == 1
    assert "clave desconocida" in result.stdout


def test_cli_reports_missing_project(cli_in: Path) -> None:
    from typer.testing import CliRunner

    from novela.cli import app

    result = CliRunner().invoke(app, ["bible", "inexistente"])
    assert result.exit_code == 1
    assert "no existe" in result.stdout
