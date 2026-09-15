"""Jerarquia de errores del harness.

Regla dura del spec (§18): no se capturan excepciones de forma generica para
continuar en silencio. Cada situacion recuperable tiene su tipo propio.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from novela.validators.base import ValidationReport


class NovelaError(Exception):
    """Raiz de todos los errores del harness."""


class ConfigError(NovelaError):
    """Configuracion invalida: clave desconocida, rango fuera de limites, perfil inexistente."""


class SchemaRetryExhausted(NovelaError):
    """El modelo no ha producido JSON valido tras agotar `limits.max_schema_retries`."""

    def __init__(self, role: str, attempts: int, last_error: str) -> None:
        self.role = role
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"El rol '{role}' no ha devuelto JSON valido tras {attempts} intentos. "
            f"Ultimo error de validacion: {last_error}"
        )


class ValidationEscalation(NovelaError):
    """Incidencia bloqueante irresoluble: el capitulo queda ESCALATED y el proyecto PAUSED."""

    def __init__(self, chapter: int, report: ValidationReport) -> None:
        self.chapter = chapter
        self.report = report
        codes = ", ".join(sorted({issue.code for issue in report.blocking}))
        super().__init__(
            f"Capitulo {chapter} escalado: incidencias bloqueantes sin resolver ({codes})."
        )


class BudgetExceeded(NovelaError):
    """El coste acumulado alcanzaria `limits.max_cost_usd`. Se corta ANTES de la llamada."""

    def __init__(self, spent_usd: float, limit_usd: float) -> None:
        self.spent_usd = spent_usd
        self.limit_usd = limit_usd
        super().__init__(
            f"Presupuesto agotado: {spent_usd:.4f} USD gastados de un tope de {limit_usd:.2f} USD. "
            "Sube limits.max_cost_usd o reduce el alcance."
        )


class ProviderError(NovelaError):
    """Fallo del proveedor LLM: autenticacion, creditos, enrutado o disponibilidad."""


class FixtureMissing(NovelaError):
    """FakeLLM no encuentra la fixture esperada. Nunca se responde con un valor por defecto."""

    def __init__(self, key: str, path: str) -> None:
        self.key = key
        self.path = path
        super().__init__(
            f"Fixture ausente para la clave '{key}'. Se esperaba el fichero '{path}'. "
            "Regenerala con `python scripts/make_fixtures.py`."
        )


class StoreError(NovelaError):
    """Fallo de persistencia: proyecto inexistente, transaccion rota o estado incoherente."""
