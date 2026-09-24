"""Clases de la ontología que son de `quality/` (`architecture.md` § Anatomía)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TipoValidador = Literal["programático", "semántico", "programático + semántico", "formal-Lean"]
PuntoEjecucion = Literal[
    "hook de policy", "hook de capítulo", "rol editor", "gate de publicación", "export"
]
Gravedad = Literal["baja", "media", "alta"]


class Defecto(BaseModel):
    """Incumplimiento concreto de una dimensión detectado en un borrador."""

    model_config = ConfigDict(frozen=True)

    dimension: str
    gravedad: Gravedad
    descripcion: str
    localizacion: str | None = None
    clasificacion: Literal["local", "sistémico"] = "local"


class ResultadoValidador(BaseModel):
    """Lo que devuelve un validador al ejecutarse. Lleva el valor del score y si cierra el
    paso: un validador que no cierra el paso puntúa pero no suspende (RF-QUA-07)."""

    model_config = ConfigDict(frozen=True)

    nombre: str
    tipo: TipoValidador
    punto: PuntoEjecucion
    pasa: bool
    valor: float
    cierra_el_paso: bool
    detalle: str
    defectos: list[Defecto] = Field(default_factory=list)
