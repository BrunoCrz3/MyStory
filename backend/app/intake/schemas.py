"""Contratos del encargo, idénticos a `specs/openapi.yaml` (los compara el test de
conformidad). Los nombres son los de la ontología (`definitions.md` Capa 1A)."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.commons.esquemas import opcional

TipoOcasion = Literal["cumpleanos", "boda", "aniversario", "jubilacion", "nacimiento", "otra"]

Texto64 = Annotated[str, Field(min_length=1, max_length=64)]
Texto80 = Annotated[str, Field(min_length=1, max_length=80)]
Texto120 = Annotated[str, Field(min_length=1, max_length=120)]


class Comprador(BaseModel):
    identificador: Texto64
    relacion_con_destinatario: Annotated[str, Field(max_length=120)] | None = opcional()


class Destinatario(BaseModel):
    nombre: Texto120
    edad: Annotated[int, Field(ge=0, le=120)]
    rasgos: list[Annotated[str, Field(max_length=200)]] = Field(default_factory=list)
    recuerdos: list[Annotated[str, Field(max_length=2000)]] = Field(default_factory=list)
    fecha_nacimiento: date | None = None


class Ocasion(BaseModel):
    tipo: TipoOcasion
    fecha: date | None = None
    tono_esperado: Annotated[str, Field(max_length=120)] | None = None


class Dedicatoria(BaseModel):
    texto: Annotated[str, Field(min_length=1, max_length=1000)]
    firma: Annotated[str, Field(max_length=120)] | None = None


class ElementoPersonalizado(BaseModel):
    enunciado: Annotated[str, Field(min_length=1, max_length=500)]
    obligatorio: bool
    origen: Literal["formulario", "texto-libre"] = "formulario"


class TextoLibre(BaseModel):
    contenido: Annotated[str, Field(min_length=1, max_length=20000)]
    procedencia: Annotated[str, Field(max_length=120)] | None = opcional()


class VozNarrativa(BaseModel):
    persona: Literal["primera", "segunda", "tercera"] = "tercera"
    tiempo_verbal: Literal["presente", "pasado"] = "pasado"
    focalizacion: Literal["interna", "externa", "cero"] = "interna"


class BriefNovela(BaseModel):
    """Salida estructurada y validada de la entrevista."""

    comprador: Comprador
    destinatario: Destinatario
    ocasion: Ocasion
    genero: Texto80
    tono: Texto80
    dedicatoria: Dedicatoria
    premisa: Annotated[str, Field(max_length=2000)] | None = None
    elementos_personalizados: list[ElementoPersonalizado] = Field(default_factory=list)
    temas_excluidos: list[Annotated[str, Field(max_length=200)]] = Field(default_factory=list)
    palabras_prohibidas: list[Annotated[str, Field(max_length=80)]] = Field(default_factory=list)
    reglas_mundo: list[Annotated[str, Field(max_length=300)]] = Field(default_factory=list)
    textos_libres: list[TextoLibre] = Field(default_factory=list)
    voz_narrativa: VozNarrativa = Field(default_factory=VozNarrativa)
