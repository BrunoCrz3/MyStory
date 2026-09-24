"""Reloj de la instancia. Una sola función, para que el formato de fecha sea uno."""

from __future__ import annotations

from datetime import UTC, datetime


def ahora() -> str:
    """Instante actual en ISO 8601, UTC, con microsegundos: ordena bien como texto."""
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
