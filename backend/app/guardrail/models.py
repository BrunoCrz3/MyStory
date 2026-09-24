"""Clases de la ontología que son de `guardrail/` (`architecture.md` § Anatomía)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

NivelPalabraProhibida = Literal["global", "perfil", "novela"]

# Orden de restricción: ante la misma palabra en dos niveles, se informa el más específico.
RESTRICCION: dict[NivelPalabraProhibida, int] = {"global": 0, "perfil": 1, "novela": 2}


class PalabraProhibida(BaseModel):
    model_config = ConfigDict(frozen=True)

    forma: str
    nivel: NivelPalabraProhibida
    origen: str


class Coincidencia(BaseModel):
    """Detección de una palabra prohibida en un texto, con su posición en el original."""

    model_config = ConfigDict(frozen=True)

    palabra: str
    nivel: NivelPalabraProhibida
    inicio: int
    fin: int
    fragmento: str
