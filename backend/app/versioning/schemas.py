"""Formas de lectura de `versioning/`, idénticas a las del contrato."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.canon.service import HechoVigente
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


# --- Solicitud de cambio (RF-VER-06…RF-VER-09) ------------------------------------------


class NuevaSolicitudCambio(BaseModel):
    """El lector pide un cambio: **exactamente uno** de `hecho_id` o `fragmento`."""

    model_config = {
        "json_schema_extra": {"oneOf": [{"required": ["hecho_id"]}, {"required": ["fragmento"]}]}
    }

    hecho_id: UUID | None = None
    fragmento: Annotated[str, Field(max_length=2000)] | None = None
    enunciado_nuevo: Annotated[str, Field(min_length=1, max_length=500)]
    capitulo_origen: Positivo

    @model_validator(mode="after")
    def _uno_de_los_dos(self) -> NuevaSolicitudCambio:
        if (self.hecho_id is None) == (self.fragmento is None):
            raise ValueError("hace falta exactamente uno de hecho_id o fragmento")
        return self


class AnalisisImpacto(BaseModel):
    capitulos_afectados: list[Positivo]
    hechos_derivados: list[UUID] | None = opcional()


EstadoSolicitud = Literal["pendiente-de-confirmacion", "confirmada", "aplicada", "descartada"]


class SolicitudCambio(BaseModel):
    solicitud_id: UUID
    novel_id: UUID
    enunciado_nuevo: str
    capitulo_origen: Positivo
    estado: EstadoSolicitud
    hecho_afectado: HechoVigente | None = opcional()
    hecho_candidato: str | None = None
    analisis_impacto: AnalisisImpacto | None = opcional()
    version_resultante: Positivo | None = None


# --- Ficha y portada (RF-VER-04, RF-VER-05) ----------------------------------------------


class EntradaFicha(BaseModel):
    nombre: str
    descripcion: str | None = None
    capitulos: list[Positivo]


class Ficha(BaseModel):
    personajes: list[EntradaFicha]
    lugares: list[EntradaFicha]


class Portada(BaseModel):
    titulo: str
    dedicatoria: Dedicatoria
    destinatario: str | None = opcional()
    ocasion: str | None = None
