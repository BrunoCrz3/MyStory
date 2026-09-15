"""Validador de continuidad (BUILD_SPEC §9.5).

Parte determinista: contradicciones del ledger, muertos que actuan, cronologia
invertida, ubicaciones imposibles, violaciones de las reglas del mundo, deriva de
nombres y cobertura de beats.

Parte con juez LLM: voz, motivacion y tension. El juez se invoca fuera de aqui,
con un `system` distinto y sin el prompt del Escritor en contexto, para reducir
el sesgo de autoevaluacion; sus incidencias se inyectan en `judge_issues`.
"""

from __future__ import annotations

import re

from rapidfuzz.distance import Levenshtein

from novela.config import ContinuityCfg
from novela.models import CanonFact, ChapterPlan, Issue, Ledger, StoryBible
from novela.validators.base import ValidationReport, issue
from novela.validators.repetition import (
    WORD_RE,
    cosine_max,
    sentences,
    strip_accents,
    tokens,
)

#: Coseno minimo para dar un beat por cubierto por una frase del capitulo.
BEAT_MATCH_MIN = 0.20
#: Fraccion de palabras significativas de un limite que deben concurrir en una
#: misma frase para considerarla una violacion de la regla del mundo.
RULE_MATCH_MIN = 0.85
#: Longitud minima de un token candidato a deriva de nombre.
NAME_MIN_LENGTH = 4
#: Distancia de edicion maxima para considerar dos nombres el mismo.
NAME_MAX_DISTANCE = 2

CAPITALISED_RE = re.compile(r"\b([A-ZÁÉÍÓÚÑ][\wáéíóúüñ-]{2,})")
NUMBER_RE = re.compile(r"\d+")
DEAD_VALUES = frozenset({"muerto", "muerta", "fallecido", "fallecida", "difunto"})
NEGATION_WORDS = frozenset({"no", "ninguna", "ningun", "ninguno", "jamas", "nunca", "sin"})


def time_key(moment: str) -> tuple[int, ...]:
    """Ordena marcas de tiempo narrativas comparando sus numeros en orden."""
    return tuple(int(value) for value in NUMBER_RE.findall(moment))


def _check_fact_conflicts(ledger: Ledger, chapter: int, report: ValidationReport) -> None:
    grouped: dict[tuple[str, str], list[CanonFact]] = {}
    for fact in ledger.current_facts():
        grouped.setdefault((fact.subject, fact.predicate), []).append(fact)
    conflicts = 0
    for (subject, predicate), facts in sorted(grouped.items()):
        values = {fact.value for fact in facts}
        if len(values) < 2:
            continue
        conflicts += 1
        report.issues.append(
            issue(
                "CONT-FACT-CONFLICT",
                f"Dos hechos vigentes incompatibles sobre {subject}.{predicate}: "
                f"{' / '.join(sorted(values))}. Revoca el que haya dejado de ser cierto.",
                chapter=chapter,
                evidence=", ".join(sorted(fact.id for fact in facts)),
            )
        )
    report.metrics["cont.fact_conflicts"] = float(conflicts)


def _acts_in_text(name: str, text: str) -> str | None:
    """Devuelve la frase en la que `name` ejerce de sujeto de una accion, si la hay."""
    first = name.split()[0]
    for sentence in sentences(text):
        words = WORD_RE.findall(sentence)
        if first.lower() not in [word.lower() for word in words]:
            continue
        index = [word.lower() for word in words].index(first.lower())
        following = words[index + 1 : index + 3]
        if any(strip_accents(word.lower()) not in {"y", "de", "del", "la"} for word in following):
            return sentence
    return None


def _check_dead_acts(
    text: str, bible: StoryBible, ledger: Ledger, chapter: int, report: ValidationReport
) -> None:
    dead = 0
    for fact in ledger.current_facts():
        if fact.predicate != "estado_vital" or strip_accents(fact.value.lower()) not in DEAD_VALUES:
            continue
        if fact.chapter_established >= chapter:
            continue
        character = bible.character_by_id(fact.subject)
        if character is None:
            continue
        span = _acts_in_text(character.name, text)
        if span is None:
            continue
        dead += 1
        report.issues.append(
            issue(
                "CONT-DEAD-ACTS",
                f"{character.name} murió en el capítulo {fact.chapter_established} y aquí actúa. "
                "Elimina su intervención o revoca el hecho con una explicación en el canon.",
                chapter=chapter,
                span=span[:120],
                evidence=fact.id,
            )
        )
    report.metrics["cont.dead_acting"] = float(dead)


def _check_timeline(
    plan: ChapterPlan, previous: ChapterPlan | None, chapter: int, report: ValidationReport
) -> None:
    report.metrics["cont.timeline_inverted"] = 0.0
    if previous is None:
        return
    declared_flashback = "flashback" in strip_accents(plan.dramatic_function.lower())
    if declared_flashback:
        return
    start, end = time_key(plan.story_time_start), time_key(previous.story_time_end)
    if not start or not end or start >= end:
        return
    report.metrics["cont.timeline_inverted"] = 1.0
    report.issues.append(
        issue(
            "CONT-TIMELINE",
            f"El capítulo empieza en «{plan.story_time_start}», antes del final del capítulo "
            f"anterior («{previous.story_time_end}»), y el plan no declara flashback.",
            chapter=chapter,
            evidence=f"{previous.story_time_end} -> {plan.story_time_start}",
        )
    )


def _check_location(
    plan: ChapterPlan,
    previous: ChapterPlan | None,
    bible: StoryBible,
    chapter: int,
    report: ValidationReport,
) -> None:
    """Mismo personaje en dos localizaciones con intervalos SOLAPADOS y sin transito narrado.

    Cambiar de sitio entre dos capitulos consecutivos es movimiento normal: solo
    es imposible si los intervalos temporales se pisan.
    """
    report.metrics["cont.location_impossible"] = 0.0
    if previous is None or previous.pov_character_id != plan.pov_character_id:
        return

    start, previous_end = time_key(plan.story_time_start), time_key(previous.story_time_end)
    overlapping = bool(start) and bool(previous_end) and start < previous_end
    if not overlapping or set(plan.location_ids) & set(previous.location_ids):
        return

    names = {location.id: location.name for location in bible.locations}
    here = sorted(names.get(item, item) for item in plan.location_ids)
    there = sorted(names.get(item, item) for item in previous.location_ids)
    report.metrics["cont.location_impossible"] = 1.0
    report.issues.append(
        issue(
            "CONT-LOCATION-IMPOSSIBLE",
            f"El punto de vista está en {here} durante un intervalo que se solapa con el del "
            f"capítulo {previous.number} en {there}, y no se narra ningún tránsito.",
            chapter=chapter,
            evidence=f"{previous.story_time_end} / {plan.story_time_start}",
        )
    )


def _check_rule_violations(
    text: str, bible: StoryBible, chapter: int, report: ValidationReport
) -> None:
    violations = 0
    chapter_sentences = sentences(text)
    for limit in bible.speculative_premise.limits:
        content = [word for word in tokens(limit) if word not in NEGATION_WORDS]
        if len(content) < 3:
            continue
        for sentence in chapter_sentences:
            present = set(tokens(sentence))
            hits = sum(1 for word in content if word in present)
            if hits / len(content) < RULE_MATCH_MIN:
                continue
            violations += 1
            report.issues.append(
                issue(
                    "CONT-RULE-VIOLATION",
                    f"El capítulo ejerce una capacidad que el canon prohíbe: «{limit}». "
                    "Reescribe la escena respetando el límite o cambia el canon explícitamente.",
                    chapter=chapter,
                    span=sentence[:120],
                    evidence=limit,
                )
            )
            break
    report.metrics["cont.rule_violations"] = float(violations)


def _check_name_drift(
    text: str, bible: StoryBible, ledger: Ledger, chapter: int, report: ValidationReport
) -> None:
    canonical = {
        token
        for name in [*bible.entity_names(), *ledger.entities]
        for token in name.split()
        if len(token) >= NAME_MIN_LENGTH
    }
    lowered = {token.lower() for token in canonical}
    drifted: dict[str, str] = {}
    for candidate in CAPITALISED_RE.findall(text):
        if len(candidate) < NAME_MIN_LENGTH or candidate.lower() in lowered:
            continue
        for reference in canonical:
            if candidate[0].lower() != reference[0].lower():
                continue
            if Levenshtein.distance(candidate.lower(), reference.lower()) <= NAME_MAX_DISTANCE:
                drifted[candidate] = reference
                break
    report.metrics["cont.name_drift"] = float(len(drifted))
    for candidate, reference in sorted(drifted.items()):
        report.issues.append(
            issue(
                "CONT-NAME-DRIFT",
                f"«{candidate}» se parece demasiado a la entidad canónica «{reference}». "
                "Usa el nombre exacto del canon o registra el alias en el glosario.",
                chapter=chapter,
                evidence=f"{candidate} ~ {reference}",
            )
        )


def _check_beat_coverage(
    text: str, plan: ChapterPlan, cfg: ContinuityCfg, chapter: int, report: ValidationReport
) -> None:
    beats = plan.all_beats()
    chapter_sentences = sentences(text)
    missing = [beat for beat in beats if cosine_max(beat, chapter_sentences) < BEAT_MATCH_MIN]
    coverage = 1.0 if not beats else (len(beats) - len(missing)) / len(beats)
    report.metrics["cont.beat_coverage"] = round(coverage, 4)
    if coverage >= cfg.beat_coverage_min:
        return
    report.issues.append(
        issue(
            "CONT-BEAT-MISSING",
            f"Cobertura de beats {coverage:.0%}, por debajo del mínimo "
            f"{cfg.beat_coverage_min:.0%}. Sin narrar: {'; '.join(missing[:2])}",
            chapter=chapter,
            evidence="; ".join(missing[:3]),
        )
    )


def validate(
    text: str,
    *,
    plan: ChapterPlan,
    previous_plan: ChapterPlan | None,
    bible: StoryBible,
    ledger: Ledger,
    cfg: ContinuityCfg,
    chapter: int,
    judge_issues: list[Issue] | None = None,
) -> ValidationReport:
    """Las siete comprobaciones deterministas de §9.5 mas las del juez, si las hay."""
    report = ValidationReport()
    _check_fact_conflicts(ledger, chapter, report)
    _check_dead_acts(text, bible, ledger, chapter, report)
    _check_timeline(plan, previous_plan, chapter, report)
    _check_location(plan, previous_plan, bible, chapter, report)
    _check_rule_violations(text, bible, chapter, report)
    _check_name_drift(text, bible, ledger, chapter, report)
    _check_beat_coverage(text, plan, cfg, chapter, report)
    report.issues.extend(judge_issues or [])
    report.metrics["cont.judge_issues"] = float(len(judge_issues or []))
    return report
