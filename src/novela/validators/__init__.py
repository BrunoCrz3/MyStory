"""Validadores deterministas y semideterministas del harness (BUILD_SPEC §9).

Un validador nunca escribe en el estado del mundo: solo devuelve incidencias.
"""

from novela.validators.base import Issue, Severity, ValidationReport, merge

__all__ = ["Issue", "Severity", "ValidationReport", "merge"]
