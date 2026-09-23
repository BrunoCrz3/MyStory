"""Contratos de `quality/` (RI-02)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.quality.models import AlcanceDelDefecto, Defecto, Eje


class _Esquema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PeticionDeCritica(_Esquema):
    escena_id: int
    version: int
    texto: str
    brief: str | None = None
    restriccion_de_destino: str | None = None
    personajes_presentes: list[int] = []
    pov_personaje_id: int | None = None


class DefectoDetectado(_Esquema):
    """Un defecto antes de guardarse. El servicio le pone alcance y gravedad."""

    dimension: str
    descripcion: str
    eje: Eje | None = None
    gravedad: str = "media"
    localizacion: str | None = None


class Puntuacion(_Esquema):
    dimension: str
    valor: float | None
    umbral: float | None
    suspende: bool
    motivo: str | None = None


class Critica(_Esquema):
    """El `Informe de critica` completo: la fila mas lo que cuelga de ella."""

    id: int
    escena_id: int
    version: int
    fase_de_medicion: bool
    escenas_aceptadas: int
    puntuaciones: list[Puntuacion]
    defectos: list[Defecto]


class Regresion(_Esquema):
    """Una dimension que la correccion ha empeorado (A-50, RF-QUA-08)."""

    dimension: str
    valor_anterior: float
    valor_nuevo: float
    version_anterior: int


class ResultadoDeHigiene(_Esquema):
    pasa: bool
    fallos: list[str]
    no_evaluables: list[str]


__all__ = [
    "AlcanceDelDefecto",
    "Critica",
    "DefectoDetectado",
    "PeticionDeCritica",
    "Puntuacion",
    "Regresion",
    "ResultadoDeHigiene",
]
