"""Tipos comunes de validacion (BUILD_SPEC §5, §9).

`Issue` y `Severity` viven en `models.py` porque son contrato de datos; aqui se
reexportan para que un validador no tenga que importar de dos sitios.
"""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from novela.models import Issue, Severity

__all__ = ["Issue", "Severity", "ValidationReport", "merge"]

#: Severidad por defecto de cada codigo de incidencia (§5).
DEFAULT_SEVERITY: dict[str, Severity] = {
    "LEN-OUT-OF-RANGE": Severity.BLOCKING,
    "LEN-FORBIDDEN-FORMAT": Severity.BLOCKING,
    "BIB-NO-LIMITS": Severity.BLOCKING,
    "BIB-CONTRADICTION": Severity.BLOCKING,
    "OUT-WRONG-COUNT": Severity.BLOCKING,
    "OUT-THREAD-UNCLOSED": Severity.BLOCKING,
    "OUT-FILLER-CHAPTER": Severity.MAJOR,
    "OUT-REPEATED-FUNCTION": Severity.MAJOR,
    "CONT-FACT-CONFLICT": Severity.BLOCKING,
    "CONT-DEAD-ACTS": Severity.BLOCKING,
    "CONT-TIMELINE": Severity.BLOCKING,
    "CONT-LOCATION-IMPOSSIBLE": Severity.BLOCKING,
    "CONT-RULE-VIOLATION": Severity.BLOCKING,
    "CONT-NAME-DRIFT": Severity.MAJOR,
    "CONT-BEAT-MISSING": Severity.MAJOR,
    "CONT-VOICE-DRIFT": Severity.MAJOR,
    "REP-NGRAM": Severity.BLOCKING,
    "REP-COSINE": Severity.BLOCKING,
    "REP-IMAGE-REUSE": Severity.MAJOR,
    "REP-OPENING-TYPE": Severity.MAJOR,
    "REP-SENTENCE-OPENER": Severity.MINOR,
    "REP-LEXICAL-DIVERSITY": Severity.MINOR,
}


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issues: list[Issue] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)

    @property
    def blocking(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity is Severity.BLOCKING]

    @property
    def major(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity is Severity.MAJOR]

    @property
    def minor(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity is Severity.MINOR]

    def codes(self) -> set[str]:
        return {issue.code for issue in self.issues}


def issue(
    code: str,
    message: str,
    *,
    chapter: int | None = None,
    severity: Severity | None = None,
    span: str | None = None,
    evidence: str | None = None,
) -> Issue:
    """Construye una incidencia con la severidad por defecto de su codigo."""
    resolved = severity if severity is not None else DEFAULT_SEVERITY[code]
    return Issue(
        code=code,
        severity=resolved,
        message=message,
        chapter=chapter,
        span=span,
        evidence=evidence,
    )


def merge(*reports: ValidationReport) -> ValidationReport:
    """Une varios informes conservando todas las incidencias y todas las metricas."""
    return merge_all(reports)


def merge_all(reports: Iterable[ValidationReport]) -> ValidationReport:
    issues: list[Issue] = []
    metrics: dict[str, float] = {}
    for report in reports:
        issues.extend(report.issues)
        metrics.update(report.metrics)
    return ValidationReport(issues=issues, metrics=metrics)
