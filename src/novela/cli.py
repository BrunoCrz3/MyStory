"""CLI del harness (BUILD_SPEC §11).

La configuracion se relee en CADA invocacion: no hay estado en memoria entre
comandos ni procesos que reiniciar. Editar `novela.yaml` y volver a lanzar el
comando basta (§3.8).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Annotated, Any

import typer
import yaml
from rich.console import Console
from rich.table import Table

from novela import __version__
from novela.config import (
    Config,
    ConfigBundle,
    find_repo_root,
    get_dotted,
    project_dir,
    resolve,
    set_yaml_value,
)
from novela.errors import NovelaError
from novela.models import Issue, Severity
from novela.observability.cost import CostTracker
from novela.observability.trace import TraceWriter
from novela.orchestrator.pipeline import Pipeline
from novela.orchestrator.states import ChapterState

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Harness multiagente generador de novelas de ciencia ficción.",
)
config_app = typer.Typer(no_args_is_help=True, help="Gestión de la configuración.")
app.add_typer(config_app, name="config")
console = Console()

SEVERITY_STYLE = {
    Severity.BLOCKING: "bold red",
    Severity.MAJOR: "yellow",
    Severity.MINOR: "dim",
}


def _bundle(project_id: str | None = None, **flags: Any) -> ConfigBundle:
    """Punto unico de resolucion de configuracion para todos los comandos."""
    bundle = resolve(project_id=project_id, flags=dict(flags))
    for warning in bundle.warnings:
        console.print(f"[yellow]Aviso de configuración:[/yellow] {warning}")
    return bundle


def _pipeline(project_id: str, **flags: Any) -> tuple[Pipeline, ConfigBundle]:
    bundle = _bundle(project_id, **flags)
    return Pipeline.open(bundle.config, bundle.repo_root, project_id), bundle


def _print_issues(issues: list[Issue]) -> None:
    if not issues:
        console.print("[green]Sin incidencias.[/green]")
        return
    table = Table("Código", "Sev.", "Cap.", "Mensaje", box=None, show_edge=False)
    for item in issues:
        table.add_row(
            item.code,
            f"[{SEVERITY_STYLE[item.severity]}]{item.severity.value}[/]",
            "-" if item.chapter is None else str(item.chapter),
            item.message,
        )
    console.print(table)


def _fail(error: NovelaError) -> None:
    console.print(f"[bold red]{type(error).__name__}:[/bold red] {error}")
    raise typer.Exit(code=1)


@app.command()
def init(
    premise: Annotated[str, typer.Argument(help="Premisa de partida de la novela.")],
    project_id: Annotated[str, typer.Option("--project-id", help="Identificador.")] = "novela",
    chapters: Annotated[int | None, typer.Option("--chapters")] = None,
    profile: Annotated[str | None, typer.Option("--profile")] = None,
) -> None:
    """Crea el proyecto y congela su configuración de partida."""
    try:
        bundle = _bundle(None, **{"novel.chapters": chapters, "profile": profile})
        pipeline = Pipeline.open(bundle.config, bundle.repo_root, project_id)
        pipeline.init(
            premise,
            resolved_yaml=yaml.safe_dump(
                bundle.config.model_dump(mode="json"), allow_unicode=True, sort_keys=False
            ),
        )
    except NovelaError as error:
        _fail(error)
    console.print(f"[green]Proyecto '{project_id}' creado[/green] en out/{project_id}/")
    console.print(f"Capítulos: {bundle.config.novel.chapters} · Perfil: {bundle.config.profile}")


@app.command()
def bible(
    project_id: str,
    approve: Annotated[bool, typer.Option("--approve")] = False,
    regenerate: Annotated[bool, typer.Option("--regenerate")] = False,
) -> None:
    """Genera o muestra la biblia narrativa (fase 1)."""
    try:
        pipeline, _ = _pipeline(project_id)
        story, report = pipeline.build_bible(regenerate=regenerate)
        console.print(f"[bold]{story.logline}[/bold]")
        _print_issues(report.issues)
        if approve and not report.blocking:
            from novela.orchestrator.states import ProjectState

            pipeline.store.set_project_state(ProjectState.BIBLE_APPROVED)
            console.print("[green]Biblia aprobada.[/green]")
    except NovelaError as error:
        _fail(error)


@app.command()
def outline(
    project_id: str,
    approve: Annotated[bool, typer.Option("--approve")] = False,
    regenerate: Annotated[bool, typer.Option("--regenerate")] = False,
) -> None:
    """Genera o muestra la escaleta (fase 2)."""
    try:
        pipeline, bundle = _pipeline(project_id)
        plan, report = pipeline.build_outline(regenerate=regenerate)
        table = Table("Cap.", "Título", "Función", "POV", box=None)
        for chapter in plan.chapters:
            table.add_row(
                str(chapter.number),
                chapter.working_title,
                chapter.dramatic_function,
                chapter.pov_character_id,
            )
        console.print(table)
        _check_chapter_drift(pipeline, bundle.config, len(plan.chapters))
        _print_issues(report.issues)
        if approve and not report.blocking:
            from novela.orchestrator.states import ProjectState

            pipeline.store.set_project_state(ProjectState.OUTLINE_APPROVED)
            console.print("[green]Escaleta aprobada.[/green]")
    except NovelaError as error:
        _fail(error)


def _check_chapter_drift(pipeline: Pipeline, config: Config, planned: int) -> None:
    """Si N cambia con la escaleta ya aprobada, se avisa y NO se trunca (§3.8)."""
    if planned == config.novel.chapters:
        return
    console.print(
        f"[yellow]Aviso:[/yellow] la escaleta tiene {planned} capítulos y la configuración pide "
        f"{config.novel.chapters}. El sistema no trunca ni improvisa: redistribuye la trama y "
        f"ejecuta `novela outline {pipeline.project_id} --regenerate` para regenerarla."
    )


@app.command()
def write(
    project_id: str,
    first: Annotated[int, typer.Option("--from")] = 1,
    last: Annotated[int | None, typer.Option("--to")] = None,
) -> None:
    """Escribe los capítulos indicados (fase 3), estrictamente en secuencia."""
    try:
        pipeline, bundle = _pipeline(project_id)
        end = last or bundle.config.novel.chapters
        written = pipeline.write_chapters(first, end)
        console.print(f"[green]Capítulos escritos:[/green] {written or 'ninguno (ya estaban)'}")
        status(project_id)
    except NovelaError as error:
        _fail(error)


@app.command()
def review(project_id: str) -> None:
    """Revisión global del manuscrito (fase 4)."""
    try:
        pipeline, _ = _pipeline(project_id)
        result = pipeline.review()
        console.print(f"[bold]{result.novel_title}[/bold]\n{result.synopsis}")
        _print_issues(result.corrections)
    except NovelaError as error:
        _fail(error)


@app.command()
def export(
    project_id: str,
    formats: Annotated[str, typer.Option("--format", help="md,pdf")] = "md,pdf",
) -> None:
    """Exporta el manuscrito (fase 5)."""
    try:
        pipeline, _ = _pipeline(project_id)
        produced = pipeline.export([item.strip() for item in formats.split(",") if item.strip()])
    except NovelaError as error:
        _fail(error)
    for kind, path in produced.items():
        console.print(f"[green]{kind}:[/green] {path}")


@app.command()
def run(
    project_id: str,
    auto: Annotated[bool, typer.Option("--auto", help="Fases 1→5 sin intervención.")] = False,
) -> None:
    """Ejecuta el pipeline completo."""
    if not auto:
        console.print("Usa `--auto` para ejecutar las fases 1→5 sin puntos de control.")
        raise typer.Exit(code=1)
    try:
        pipeline, _ = _pipeline(project_id)
        produced = pipeline.run_auto()
    except NovelaError as error:
        _fail(error)
    for kind, path in produced.items():
        console.print(f"[green]{kind}:[/green] {path}")


@app.command()
def status(project_id: str) -> None:
    """Estado del proyecto, capítulos y capítulos obsoletos."""
    try:
        pipeline, bundle = _pipeline(project_id)
        console.print(
            f"Proyecto [bold]{project_id}[/bold] · estado {pipeline.store.project_state()}"
        )
        table = Table("Cap.", "Estado", "Unidades", "Obsoleto", box=None)
        stale = set(pipeline.store.stale_chapters())
        for number in range(1, bundle.config.novel.chapters + 1):
            version = pipeline.store.latest_chapter(number)
            table.add_row(
                str(number),
                pipeline.store.chapter_state(number) or ChapterState.PLANNED.value,
                "-" if version is None else str(version.unit_count),
                "sí" if number in stale else "no",
            )
        console.print(table)
    except NovelaError as error:
        _fail(error)


@app.command()
def continuity(project_id: str) -> None:
    """Panel de continuidad: hechos vigentes, hilos y cronología."""
    try:
        pipeline, _ = _pipeline(project_id)
        ledger = pipeline.store.load_ledger()
    except NovelaError as error:
        _fail(error)
    facts = Table("Hecho", "Sujeto", "Predicado", "Valor", "Cap.", box=None)
    for fact in ledger.current_facts():
        facts.add_row(
            fact.id, fact.subject, fact.predicate, fact.value, str(fact.chapter_established)
        )
    console.print(facts)
    threads = ledger.open_threads()
    console.print(
        "[green]Sin hilos abiertos.[/green]"
        if not threads
        else "Hilos abiertos: " + ", ".join(f"{t.id} ({t.question})" for t in threads)
    )
    for moment in ledger.timeline:
        console.print(f"  · {moment}")


@app.command()
def cost(project_id: str) -> None:
    """Coste observado, agregado por rol y por capítulo."""
    bundle = _bundle(project_id)
    directory = project_dir(bundle.repo_root, project_id)
    tracker = CostTracker(directory / "cost.json")
    total = CostTracker.load_total(tracker.path)
    console.print(
        f"Coste observado del proyecto: [bold]{total:.4f} USD[/bold] "
        f"(tope {bundle.config.limits.max_cost_usd:.2f} USD)"
    )
    events = TraceWriter(directory / "trace.jsonl").read_all()
    table = Table("Rol", "Llamadas", "Tokens ent.", "Tokens sal.", "USD", box=None)
    roles: dict[str, list[float]] = {}
    for event in events:
        row = roles.setdefault(str(event.get("role")), [0.0, 0.0, 0.0, 0.0])
        row[0] += 1
        row[1] += _number(event.get("input_tokens"))
        row[2] += _number(event.get("output_tokens"))
        row[3] += _number(event.get("cost_usd"))
    for role, row in sorted(roles.items()):
        table.add_row(role, f"{row[0]:.0f}", f"{row[1]:.0f}", f"{row[2]:.0f}", f"{row[3]:.4f}")
    console.print(table)


def _number(value: object) -> float:
    """Convierte un campo de `trace.jsonl` a float sin confiar en su tipo declarado."""
    return float(value) if isinstance(value, (int, float)) else 0.0


@app.command()
def demo() -> None:
    """Proyecto de ejemplo con FakeLLM, offline y en menos de diez segundos."""
    root = find_repo_root()
    directory = project_dir(root, "demo")
    if directory.exists():
        shutil.rmtree(directory)
    bundle = resolve(
        repo_root=root,
        flags={"llm.provider": "fake", "profile": "micro"},
        environ={},
    )
    pipeline = Pipeline.open(bundle.config, root, "demo")
    pipeline.init(
        "Una ingeniera de una estación minera descubre que el oráculo que predice accidentes "
        "lleva meses sirviendo para provocarlos.",
        resolved_yaml=yaml.safe_dump(
            bundle.config.model_dump(mode="json"), allow_unicode=True, sort_keys=False
        ),
    )
    try:
        produced = pipeline.run_auto()
    except NovelaError as error:
        _fail(error)
    console.print(
        f"[green]Demo completa[/green] · {bundle.config.novel.chapters} capítulos de "
        f"{bundle.config.novel.length.target} {bundle.config.novel.length.unit}"
    )
    for kind, path in produced.items():
        console.print(f"[green]{kind}:[/green] {path.relative_to(root)}")


# --------------------------------------------------------------------------
# novela config ...
# --------------------------------------------------------------------------
@config_app.command("init")
def config_init() -> None:
    """Crea novela.yaml a partir de la plantilla comentada."""
    root = find_repo_root()
    target, template = root / "novela.yaml", root / "novela.example.yaml"
    if target.exists():
        console.print(f"[yellow]{target.name} ya existe: no se sobrescribe.[/yellow]")
        raise typer.Exit(code=0)
    shutil.copyfile(template, target)
    console.print(f"[green]Creado[/green] {target.name} conservando los comentarios.")


@config_app.command("show")
def config_show(
    resolved: Annotated[bool, typer.Option("--resolved")] = False,
    project_id: Annotated[str | None, typer.Option("--project")] = None,
) -> None:
    """Muestra la configuración efectiva, con el origen de cada clave si se pide."""
    bundle = _bundle(project_id)
    if not resolved:
        console.print(
            yaml.safe_dump(
                bundle.config.model_dump(mode="json"), allow_unicode=True, sort_keys=False
            )
        )
        return
    table = Table("Clave", "Valor", "Origen", box=None)
    for key, origin in sorted(bundle.origins.items()):
        try:
            value = get_dotted(bundle.config, key)
        except NovelaError:
            continue
        table.add_row(key, str(value), origin)
    console.print(table)


@config_app.command("get")
def config_get(
    key: str, project_id: Annotated[str | None, typer.Option("--project")] = None
) -> None:
    """Imprime el valor efectivo de una clave."""
    try:
        console.print(get_dotted(_bundle(project_id).config, key))
    except NovelaError as error:
        _fail(error)


@config_app.command("set")
def config_set(
    key: str,
    value: str,
    project_id: Annotated[str | None, typer.Option("--project")] = None,
) -> None:
    """Escribe una clave en novela.yaml conservando los comentarios del fichero."""
    try:
        bundle = _bundle(project_id)
        previous = get_dotted(bundle.config, key)
        target = (
            project_dir(bundle.repo_root, project_id) / "config.yaml"
            if project_id
            else bundle.repo_root / "novela.yaml"
        )
        set_yaml_value(target, key, yaml.safe_load(value))
        updated = resolve(repo_root=bundle.repo_root, project_id=project_id)
        _record_change(bundle.repo_root, project_id, key, previous, get_dotted(updated.config, key))
    except NovelaError as error:
        _fail(error)
    console.print(f"[green]{key}[/green] = {value}  →  {target}")


def _record_change(root: Path, project_id: str | None, key: str, old: object, new: object) -> None:
    if project_id is None or old == new:
        return
    Pipeline.open(
        resolve(repo_root=root, project_id=project_id).config, root, project_id
    ).log_config_change(key, old, new)


@config_app.command("validate")
def config_validate(project_id: Annotated[str | None, typer.Option("--project")] = None) -> None:
    """Valida la configuración sin ejecutar nada. Código de salida 0 o 1."""
    try:
        bundle = resolve(project_id=project_id)
    except NovelaError as error:
        console.print(f"[bold red]{type(error).__name__}:[/bold red] {error}")
        raise typer.Exit(code=1) from error
    for warning in bundle.warnings:
        console.print(f"[yellow]Aviso:[/yellow] {warning}")
    console.print(f"[green]Configuración válida.[/green] novela-agent {__version__}")
    raise typer.Exit(code=0)
