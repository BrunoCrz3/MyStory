"""Contratos HTTP de `canon/`, idénticos a `specs/openapi.yaml` (los compara el test de
conformidad)."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.commons.esquemas import opcional


class HechoVigente(BaseModel):
    """`Hecho` del contrato: enunciado verdadero en la versión consultada, con quién lo usa."""

    hecho_id: UUID
    enunciado: str
    estado: Literal["propuesto", "adoptado", "descartado", "retconeado", "refutado"]
    origen: Literal["brief", "texto-libre", "extraccion"] | None = opcional()
    capitulo_establece: Annotated[int, Field(ge=1)] | None = None
    capitulos_usan: list[Annotated[int, Field(ge=1)]]
    fragmento_soporte: str | None = None
