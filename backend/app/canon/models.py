"""Clases de la ontología que son de `canon/` (`architecture.md` § Anatomía)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EstadoHecho = Literal["propuesto", "adoptado", "descartado", "retconeado", "refutado"]
OrigenHecho = Literal["brief", "texto-libre", "extraccion"]
EstadoPromesa = Literal["pendiente", "pagada", "rota"]


class HechoNuevo(BaseModel):
    """Un hecho que el extractor propone para un capítulo recién aceptado."""

    model_config = ConfigDict(frozen=True)

    enunciado: str
    tipo: str
    fragmento_soporte: str


class PromesaNueva(BaseModel):
    model_config = ConfigDict(frozen=True)

    enunciado: str
    tipo: str


class Consolidacion(BaseModel):
    """Lo que entra en la story bible al aceptar un capítulo. Lo arma `process/` con la
    extracción; `canon/` no sabe de dónde viene."""

    capitulo_id: str
    numero: int
    hechos_nuevos: list[HechoNuevo] = Field(default_factory=list)
    hechos_usados: list[str] = Field(default_factory=list)
    promesas_abiertas: list[PromesaNueva] = Field(default_factory=list)
    promesas_pagadas: list[str] = Field(default_factory=list)
    personajes_presentes: list[str] = Field(default_factory=list)
    ubicaciones: dict[str, str] = Field(default_factory=dict)
    momento: int | None = None


class HechoPropuesto(BaseModel):
    model_config = ConfigDict(frozen=True)

    hecho_id: str
    enunciado: str
    tipo: str
    fragmento_soporte: str


class ResultadoConsolidacion(BaseModel):
    adoptados: list[HechoPropuesto] = Field(default_factory=list)
    descartados: list[HechoPropuesto] = Field(default_factory=list)
    sin_fragmento: list[HechoNuevo] = Field(default_factory=list)
    ya_consolidado: bool = False


class Hecho(BaseModel):
    """Un hecho visto desde una versión concreta."""

    model_config = ConfigDict(frozen=True)

    hecho_id: str
    enunciado: str
    tipo: str
    estado: EstadoHecho
    origen: OrigenHecho
    capitulo_establece: int | None
    capitulos_usan: list[int]
    fragmento_soporte: str | None


class Snapshot(BaseModel):
    """Estado derivado del mundo al cierre de un capítulo (D-12)."""

    model_config = ConfigDict(frozen=True)

    numero: int
    momento: int | None
    personajes_presentes: list[str]
    ubicaciones: dict[str, str]
    hechos: list[str]
    promesas_pendientes: list[str]


class Promesa(BaseModel):
    model_config = ConfigDict(frozen=True)

    promesa_id: str
    enunciado: str
    tipo: str
    estado: EstadoPromesa
    capitulo_apertura: int
    capitulo_pago: int | None
