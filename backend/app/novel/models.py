"""Clases de la ontología que son de `novel/` (`architecture.md` § Anatomía)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

# Los estados de `domain-knowledge.md` § Estados, uno a uno y sin añadidos.
EstadoNovela = Literal[
    "Configurando",
    "Planificando",
    "Escribiendo",
    "Validando",
    "Publicando",
    "Publicada",
    "Regenerando",
    "Detenida",
]
EstadoCapitulo = Literal[
    "Pendiente",
    "Escribiendo",
    "Validando",
    "Aceptado",
    "Reescribiendo",
    "Agotado",
    "Obsoleto",
]
ESTADOS_TERMINALES_NOVELA: frozenset[str] = frozenset({"Publicada", "Detenida"})


class ReglaMundo(BaseModel):
    model_config = ConfigDict(frozen=True)

    enunciado: str
    origen: str


class Personaje(BaseModel):
    model_config = ConfigDict(frozen=True)

    nombre: str
    deseo: str | None = None
    herida: str | None = None
    rol_narrativo: str | None = None
    voz: str | None = None
    es_destinatario: bool = False
    fecha_nacimiento: str | None = None


class Lugar(BaseModel):
    model_config = ConfigDict(frozen=True)

    nombre: str
    geografia: str | None = None
    atmosfera: str | None = None


class HiloTrama(BaseModel):
    model_config = ConfigDict(frozen=True)

    nombre: str
    pregunta_dramatica: str | None = None
