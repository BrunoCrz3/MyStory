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


class Score(BaseModel):
    """Resultado de un validador ejecutado, uno por validador y por intento (RF-OBS-03)."""

    model_config = ConfigDict(frozen=True)

    validador: str
    valor: float
    pasa: bool
    cierra_el_paso: bool
    detalle: str


DecisionInforme = Literal["aceptar", "devolver", "agotar", "detener"]


class InformeCritica(BaseModel):
    """Defectos detectados, clasificados y priorizados en un intento de un capítulo, con los
    scores de los validadores que corrieron y la decisión del policy engine."""

    model_config = ConfigDict(frozen=True)

    informe_id: str
    capitulo_id: str
    intento: int
    decision: DecisionInforme
    creado_en: str
    defectos: list[Defecto]
    scores: list[Score]


class AfirmacionDestinatario(BaseModel):
    """Un hecho personal que el capítulo afirma sobre el destinatario, con su cita y, a juicio
    del judge, dónde se apoya (D-13, A-108)."""

    model_config = ConfigDict(extra="forbid")

    afirmacion: str
    fragmento: str
    apoyo: Literal["brief", "texto-libre", "ninguno"]


class TemaExcluidoVisto(BaseModel):
    """Si un tema excluido aparece en el capítulo, aunque no se nombre (D-13)."""

    model_config = ConfigDict(extra="forbid")

    tema: str
    aparece: bool
    fragmento: str


class ContextoJudge(BaseModel):
    """Lo que los validadores del rol editor necesitan además de la salida del judge: contra
    qué se coteja una afirmación y qué temas vetó el comprador."""

    model_config = ConfigDict(frozen=True)

    destinatario: str
    soporte: list[str]
    temas_excluidos: list[str]
    texto: str
