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


# --- Brief parcial (TO-037) --------------------------------------------------------------
# Los mismos campos que `BriefNovela`, todos opcionales, también los anidados, y sin
# longitud mínima. Conservan tipos, `enum`, longitudes máximas y rangos: un valor mal
# formado sigue siendo un 422. Solo lo acepta la validación del brief.


class CompradorParcial(BaseModel):
    identificador: Annotated[str, Field(max_length=64)] | None = opcional()
    relacion_con_destinatario: Annotated[str, Field(max_length=120)] | None = opcional()


class DestinatarioParcial(BaseModel):
    nombre: Annotated[str, Field(max_length=120)] | None = opcional()
    edad: Annotated[int, Field(ge=0, le=120)] | None = opcional()
    rasgos: list[Annotated[str, Field(max_length=200)]] | None = opcional()
    recuerdos: list[Annotated[str, Field(max_length=2000)]] | None = opcional()
    fecha_nacimiento: date | None = None


class OcasionParcial(BaseModel):
    tipo: TipoOcasion | None = opcional()
    fecha: date | None = None
    tono_esperado: Annotated[str, Field(max_length=120)] | None = None


class DedicatoriaParcial(BaseModel):
    texto: Annotated[str, Field(max_length=1000)] | None = opcional()
    firma: Annotated[str, Field(max_length=120)] | None = None


class ElementoPersonalizadoParcial(BaseModel):
    enunciado: Annotated[str, Field(max_length=500)] | None = opcional()
    obligatorio: bool | None = opcional()
    origen: Literal["formulario", "texto-libre"] = "formulario"


class TextoLibreParcial(BaseModel):
    contenido: Annotated[str, Field(max_length=20000)] | None = opcional()
    procedencia: Annotated[str, Field(max_length=120)] | None = opcional()


class BriefNovelaParcial(BaseModel):
    """El brief mientras se rellena. **No sirve para crear una novela.**"""

    comprador: CompradorParcial | None = opcional()
    destinatario: DestinatarioParcial | None = opcional()
    ocasion: OcasionParcial | None = opcional()
    genero: Annotated[str, Field(max_length=80)] | None = opcional()
    tono: Annotated[str, Field(max_length=80)] | None = opcional()
    dedicatoria: DedicatoriaParcial | None = opcional()
    premisa: Annotated[str, Field(max_length=2000)] | None = None
    elementos_personalizados: list[ElementoPersonalizadoParcial] | None = opcional()
    temas_excluidos: list[Annotated[str, Field(max_length=200)]] | None = opcional()
    palabras_prohibidas: list[Annotated[str, Field(max_length=80)]] | None = opcional()
    reglas_mundo: list[Annotated[str, Field(max_length=300)]] | None = opcional()
    textos_libres: list[TextoLibreParcial] | None = opcional()
    voz_narrativa: VozNarrativa | None = opcional()


# --- Resultado de la validación ----------------------------------------------------------

TipoContradiccion = Literal["edad-vs-tono", "edad-vs-genero", "fecha-vs-edad", "otra"]


class DatoFaltante(BaseModel):
    """Un obligatorio de `BriefNovela` que no llega o llega vacío. Se repregunta."""

    campo: str
    pregunta_reintento: str | None = opcional()


class ContradiccionBrief(BaseModel):
    """Conflicto entre dos datos del comprador, por regla determinista entre campos."""

    campos: list[str]
    tipo: TipoContradiccion
    explicacion: str | None = opcional()


class FragmentoSospechoso(BaseModel):
    """Parte del texto libre que parece una instrucción al sistema. Se registra y descarta."""

    fragmento: str
    motivo: str


class HechoTextoLibre(BaseModel):
    """Un hecho leído del texto libre. Entra como propuesto."""

    enunciado: str
    origen: Literal["texto-libre"] | None = opcional(enum=["texto-libre"])


class ResultadoValidacionBrief(BaseModel):
    valido: bool
    datos_faltantes: list[DatoFaltante]
    contradicciones: list[ContradiccionBrief]
    fragmentos_sospechosos: list[FragmentoSospechoso]
    hechos_extraidos: list[HechoTextoLibre]
