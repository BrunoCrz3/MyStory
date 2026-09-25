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


class EventoNarrado(BaseModel):
    """Un `Evento` de la fábula tal como lo narra un capítulo."""

    model_config = ConfigDict(frozen=True)

    descripcion: str
    momento: int
    lugar: str | None
    personajes: list[str]
    anio: int | None = None
    edades: dict[str, int] = {}


class ExcluyenteNarrado(BaseModel):
    """Un `Evento excluyente` que el capítulo declara: el evento del capítulo en `momento`
    excluye a `personaje` (TO-065)."""

    model_config = ConfigDict(frozen=True)

    personaje: str
    tipo: Literal["muerte", "partida"]
    momento: int


class PresenciaEnEvento(BaseModel):
    """Un personaje presente en un evento, con la edad que el texto le declara ahí, si la
    declara (TO-064)."""

    model_config = ConfigDict(frozen=True)

    personaje_id: str
    edad: int | None


class EventoVigente(BaseModel):
    """Un `Evento` vigente en una versión, como lo lee la verificación formal: `momento` es el
    orden de narración y `anio`, la cronología de la historia (TO-064, TO-066)."""

    model_config = ConfigDict(frozen=True)

    evento_id: str
    capitulo_id: str
    numero: int
    momento: int
    anio: int | None
    lugar_id: str | None
    presentes: list[PresenciaEnEvento]
