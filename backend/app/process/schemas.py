"""Salidas estructuradas de los roles que orquesta `process/`.

Todas las propiedades son obligatorias, porque la salida estructurada estricta lo exige; lo
que puede faltar se declara nulable.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.commons.esquemas import opcional
from app.novel.service import EstadoNovela

TipoRestriccion = Literal["estado_final", "revelacion", "posicion_personaje"]
TipoAlcance = Literal["personaje", "lugar", "promesa", "hilo"]


class _Salida(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EntidadAlcance(_Salida):
    tipo: TipoAlcance
    nombre: str


class RestriccionDestino(_Salida):
    tipo: TipoRestriccion
    enunciado: str
    alcance: list[EntidadAlcance]


class PlanCapitulo(_Salida):
    numero: int
    titulo_provisional: str
    funcion_dramatica: str
    pov: str
    lugar: str
    estado_entrada: str
    restriccion: RestriccionDestino
    elementos: list[str]


class PersonajePlan(_Salida):
    nombre: str
    deseo: str
    herida: str
    rol_narrativo: str
    voz: str
    es_destinatario: bool


class LugarPlan(_Salida):
    nombre: str
    geografia: str
    atmosfera: str


class HiloPlan(_Salida):
    nombre: str
    pregunta_dramatica: str


class Esquema(_Salida):
    """Plan de capítulos con sus funciones dramáticas y sus restricciones de destino."""

    titulo: str
    premisa: str
    personajes: list[PersonajePlan]
    lugares: list[LugarPlan]
    hilos: list[HiloPlan]
    capitulos: list[PlanCapitulo]


class BorradorCapitulo(_Salida):
    """Salida del redactor y del editor: el capítulo aún no aceptado."""

    titulo: str
    texto: str


class HechoExtraido(_Salida):
    enunciado: str
    tipo: str
    fragmento_soporte: str


class EdadDeclarada(_Salida):
    personaje: str
    edad: int


class EventoExtraido(_Salida):
    """`anio` es el año de la historia en que ocurre, y `edades`, las que el texto declara de
    los presentes: los dos solo si el capítulo los dice explícitamente (TO-064)."""

    descripcion: str
    orden: int
    lugar: str | None
    personajes: list[str]
    anio: int | None
    edades: list[EdadDeclarada]


class ExcluyenteExtraido(_Salida):
    """Una muerte o una partida definitiva que el texto declara explícitamente (TO-065), en el
    evento de este capítulo con ese `orden`."""

    personaje: str
    tipo: Literal["muerte", "partida"]
    orden: int


class PromesaExtraida(_Salida):
    enunciado: str
    tipo: str


class Ubicacion(_Salida):
    personaje: str
    lugar: str


class Extraccion(_Salida):
    """Lectura del capítulo aceptado. `hechos_usados`, `promesas_pagadas` y
    `promesas_reabiertas` citan los alias (`H1`, `P1`) de la lista que recibe el extractor, no
    identificadores internos. Reabrir es lo que hace un capítulo reescrito con la promesa que
    ya abría su versión anterior: la cita por su alias en vez de abrir otra igual (TO-047)."""

    hechos_nuevos: list[HechoExtraido]
    hechos_usados: list[str]
    eventos: list[EventoExtraido]
    excluyentes: list[ExcluyenteExtraido]
    promesas_abiertas: list[PromesaExtraida]
    promesas_pagadas: list[str]
    promesas_reabiertas: list[str]
    elementos_presentes: list[str]
    personajes_presentes: list[str]
    ubicaciones: list[Ubicacion]
    resumen: str
    gancho_cierre: str


class Generacion(BaseModel):
    """Una generación completa, inicial o dirigida: el recurso que el frontend sondea."""

    generacion_id: UUID
    novel_id: UUID
    tipo: Literal["inicial", "dirigida"]
    estado: EstadoNovela
    es_terminal: bool
    intervalo_sondeo_segundos: Annotated[int, Field(ge=1)] | None
    capitulo_actual: Annotated[int, Field(ge=1)] | None = None
    capitulos_aceptados: Annotated[int, Field(ge=0)]
    total_capitulos: Annotated[int, Field(ge=1)]
    capitulos_a_regenerar: list[Annotated[int, Field(ge=1)]] | None = opcional()
    intentos_capitulo_actual: Annotated[int, Field(ge=0)] | None = opcional()
    checkpoint: Annotated[int, Field(ge=0)] | None = None
    tokens_consumidos: Annotated[int, Field(ge=0)] | None = opcional()
    coste_usd: Annotated[float, Field(ge=0)] | None = opcional()
    traza_langfuse_id: str | None = None
    detenida_por: str | None = None
    version_resultante: Annotated[int, Field(ge=1)] | None = None
    iniciada_en: datetime
    terminada_en: datetime | None = None
