"""Validador de la biblia narrativa (BUILD_SPEC §9.2).

Una tecnologia sin limites destruye el conflicto y es la primera causa de
incoherencias aguas abajo: por eso `limits` y `cost` son bloqueantes.
"""

from __future__ import annotations

from novela.models import Outline, StoryBible
from novela.validators.base import ValidationReport, issue

#: Un limite o un coste mas cortos que esto son un tramite, no una restriccion.
MIN_SUBSTANTIVE_LENGTH = 15


def _check_limits(bible: StoryBible, report: ValidationReport) -> None:
    premise = bible.speculative_premise
    trivial = [item for item in premise.limits if len(item.strip()) < MIN_SUBSTANTIVE_LENGTH]
    report.metrics["bib.limits"] = float(len(premise.limits))
    if trivial:
        report.issues.append(
            issue(
                "BIB-NO-LIMITS",
                "Hay límites triviales en la premisa especulativa: "
                f"{trivial}. Un límite debe decir qué NO puede hacer la tecnología y por qué "
                "eso genera conflicto.",
                evidence="; ".join(trivial),
            )
        )
    if len(premise.cost.strip()) < MIN_SUBSTANTIVE_LENGTH:
        report.issues.append(
            issue(
                "BIB-NO-LIMITS",
                "El coste de la premisa especulativa está vacío o es trivial. Sin coste, usar "
                "la tecnología no cuesta nada y la historia no tiene apuesta.",
                evidence=premise.cost,
            )
        )


def _check_character_contradictions(bible: StoryBible, report: ValidationReport) -> None:
    seen: dict[tuple[str, str], str] = {}
    duplicates = 0
    for character in bible.characters:
        key = (character.role.strip().lower(), character.want.strip().lower())
        if key in seen:
            duplicates += 1
            report.issues.append(
                issue(
                    "BIB-CONTRADICTION",
                    f"{character.name} y {seen[key]} comparten rol y deseo: son el mismo "
                    "personaje escrito dos veces. Diferencia el want o fúndelos.",
                    evidence=f"{character.id} / {key[0]}",
                )
            )
        seen[key] = character.name
    report.metrics["bib.duplicate_characters"] = float(duplicates)


def _check_cross_references(bible: StoryBible, outline: Outline, report: ValidationReport) -> None:
    character_ids = {character.id for character in bible.characters}
    location_ids = {location.id for location in bible.locations}
    broken = 0
    for plan in outline.chapters:
        if plan.pov_character_id not in character_ids:
            broken += 1
            report.issues.append(
                issue(
                    "BIB-CONTRADICTION",
                    f"El capítulo {plan.number} declara el POV «{plan.pov_character_id}», que no "
                    "existe en la biblia. Corrige la escaleta o añade el personaje al canon.",
                    chapter=plan.number,
                    evidence=plan.pov_character_id,
                )
            )
        for location_id in plan.location_ids:
            if location_id in location_ids:
                continue
            broken += 1
            report.issues.append(
                issue(
                    "BIB-CONTRADICTION",
                    f"El capítulo {plan.number} sitúa la acción en «{location_id}», que no existe "
                    "en la biblia.",
                    chapter=plan.number,
                    evidence=location_id,
                )
            )
    report.metrics["bib.broken_references"] = float(broken)


def validate(bible: StoryBible, *, outline: Outline | None = None) -> ValidationReport:
    report = ValidationReport()
    _check_limits(bible, report)
    _check_character_contradictions(bible, report)
    if outline is not None:
        _check_cross_references(bible, outline, report)
    return report
