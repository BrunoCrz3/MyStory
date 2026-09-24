"""Salidas del judge de prueba: las seis puntuaciones de la rúbrica con su justificación."""

from __future__ import annotations

from typing import Any

CRITERIOS = (
    "continuidad",
    "tono",
    "arco",
    "coherencia_personajes",
    "ritmo",
    "personalizacion_natural",
)


def salida_judge(**puntuaciones: float) -> dict[str, Any]:
    """Todas a 0.9 salvo las que se pasen, cada una con una justificación distinta."""
    salida: dict[str, Any] = {
        c: {"puntuacion": puntuaciones.get(c, 0.9), "justificacion": f"Justificación de {c}."}
        for c in CRITERIOS
    }
    salida["afirmaciones_destinatario"] = []
    salida["temas_excluidos"] = []
    return salida
