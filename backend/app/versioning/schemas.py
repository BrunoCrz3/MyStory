"""Formas de lectura de `versioning/`, idénticas a las del contrato."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from app.commons.esquemas import opcional
from app.intake.service import Dedicatoria
from app.novel.service import EstadoCapitulo

Positivo = Annotated[int, Field(ge=1)]


class Capitulo(BaseModel):
    numero: Positivo
    titulo: str | None = None
    estado: EstadoCapitulo
    texto: str | None = None
    palabras: Annotated[int, Field(ge=0)] | None = None
    resumen: str | None = None
    gancho_cierre: str | None = None
    pov: str | None = None
    lugar: str | None = None
    funcion_dramatica: str | None = None
    intentos: Annotated[int, Field(ge=0)] | None = opcional()
    modificado: bool = False


class CapituloIndice(BaseModel):
    """Entrada del índice navegable. Sin texto."""

    numero: Positivo
    titulo: str | None = None
    palabras: int | None = None
    modificado: bool


class VersionResumen(BaseModel):
    version: Positivo
    publicada_en: datetime
    version_anterior: Positivo | None = None
    capitulos_modificados: list[Positivo]
    motivo: str | None = None


class Version(BaseModel):
    version: Positivo
    novel_id: UUID
    titulo: str | None = None
    publicada_en: datetime
    version_anterior: Positivo | None = None
    hash: str | None = None
    dedicatoria: Dedicatoria | None = opcional()
    capitulos: list[CapituloIndice]
