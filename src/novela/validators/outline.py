"""Validador de escaleta (BUILD_SPEC §9.3).

El numero de capitulos es configuracion, nunca una constante: el recuento se
compara siempre contra `config.novel.chapters`.
"""

from __future__ import annotations

from novela.models import Outline
from novela.validators.base import ValidationReport, issue


def _check_count(outline: Outline, expected: int, report: ValidationReport) -> None:
    actual = len(outline.chapters)
    report.metrics["out.chapters"] = float(actual)
    if actual != expected:
        report.issues.append(
            issue(
                "OUT-WRONG-COUNT",
                f"La escaleta tiene {actual} capítulos y la configuración pide {expected}. "
                "Regenérala con `novela outline <pid> --regenerate`.",
                evidence=f"{actual} != {expected}",
            )
        )

    numbers = [plan.number for plan in outline.chapters]
    if numbers != list(range(1, actual + 1)):
        report.issues.append(
            issue(
                "OUT-WRONG-COUNT",
                f"La numeración de capítulos tiene huecos o repeticiones: {numbers}. "
                "Debe ser 1…N sin saltos.",
                evidence=str(numbers),
            )
        )


def _check_threads(outline: Outline, expected: int, report: ValidationReport) -> None:
    closed_at: dict[str, int] = {}
    for plan in outline.chapters:
        for thread in plan.threads_closed:
            closed_at.setdefault(thread, plan.number)

    unclosed = 0
    for plan in outline.chapters:
        for thread in plan.threads_opened:
            closing = closed_at.get(thread)
            if closing is not None and closing <= expected:
                continue
            unclosed += 1
            report.issues.append(
                issue(
                    "OUT-THREAD-UNCLOSED",
                    f"El hilo «{thread}», abierto en el capítulo {plan.number}, no se cierra en "
                    f"ningún capítulo ≤ {expected}. Ciérralo o no lo abras.",
                    chapter=plan.number,
                    evidence=thread,
                )
            )
    report.metrics["out.threads_unclosed"] = float(unclosed)


def _check_filler(outline: Outline, report: ValidationReport) -> None:
    filler = 0
    for plan in outline.chapters:
        for scene in plan.scenes:
            if [item for item in scene.new_information if item.strip()]:
                continue
            filler += 1
            report.issues.append(
                issue(
                    "OUT-FILLER-CHAPTER",
                    f"La escena «{scene.id}» del capítulo {plan.number} no aporta información "
                    "nueva: el capítulo es relleno. Dale algo que el lector no sepa aún.",
                    chapter=plan.number,
                    evidence=scene.id,
                )
            )
    report.metrics["out.filler_scenes"] = float(filler)


def _check_repeated_function(outline: Outline, report: ValidationReport) -> None:
    repeated = 0
    ordered = sorted(outline.chapters, key=lambda plan: plan.number)
    for previous, plan in zip(ordered, ordered[1:], strict=False):
        same_function = previous.dramatic_function == plan.dramatic_function
        same_pov = previous.pov_character_id == plan.pov_character_id
        same_place = set(previous.location_ids) == set(plan.location_ids)
        if not (same_function and same_pov and same_place):
            continue
        repeated += 1
        report.issues.append(
            issue(
                "OUT-REPEATED-FUNCTION",
                f"Los capítulos {previous.number} y {plan.number} repiten función dramática, "
                f"punto de vista y localización («{plan.dramatic_function}»). Uno de los dos "
                "no está haciendo nada nuevo.",
                chapter=plan.number,
                evidence=plan.dramatic_function,
            )
        )
    report.metrics["out.repeated_functions"] = float(repeated)


def validate(outline: Outline, *, expected_chapters: int) -> ValidationReport:
    report = ValidationReport()
    _check_count(outline, expected_chapters, report)
    _check_threads(outline, expected_chapters, report)
    _check_filler(outline, report)
    _check_repeated_function(outline, report)
    return report
