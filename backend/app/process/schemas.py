"""Salidas estructuradas de los roles que orquesta `process/`.

Todas las propiedades son obligatorias, porque la salida estructurada estricta lo exige; lo
que puede faltar se declara nulable.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

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
