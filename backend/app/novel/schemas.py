"""Contratos HTTP de la obra, idénticos a `specs/openapi.yaml`."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from app.commons.esquemas import opcional
from app.intake.service import BriefNovela
from app.novel.models import EstadoNovela


class NovelaResumen(BaseModel):
    novel_id: UUID
    titulo: str | None
    estado: EstadoNovela
    version_vigente: Annotated[int, Field(ge=1)] | None = None
    creada_en: datetime


class Novela(BaseModel):
    novel_id: UUID
    titulo: str | None = None
    estado: EstadoNovela
    version_vigente: Annotated[int, Field(ge=1)] | None = None
    total_capitulos: int | None = opcional()
    creada_en: datetime
    brief: BriefNovela


class ListaNovelas(BaseModel):
    items: list[NovelaResumen]
    total: Annotated[int, Field(ge=0)]
