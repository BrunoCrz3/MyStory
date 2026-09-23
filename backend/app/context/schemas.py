"""Contratos de `context/` (RI-02)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.canon.models import HechoCanonico
from app.context.models import Capa, Fragmento, NivelDeCompresion, TipoDeUso, UsoDeRecurso


class _Esquema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Referencia(_Esquema):
    """Una entidad del brief. El filtro relacional se hace con estas."""

    tipo: str
    id: int


class NuevoFragmento(_Esquema):
    escena_id: int
    texto: str
    nivel: NivelDeCompresion
    entidades: list[Referencia] = []
    embedding: list[float]


class NuevoUso(_Esquema):
    escena_id: int
    tipo: TipoDeUso
    texto: str


class PeticionDeEnsamblado(_Esquema):
    escena_id: int
    brief: str
    restriccion_de_destino: str
    entidades: list[Referencia] = []
    personajes_presentes: list[int] = []
    consulta: list[float] | None = None
    # La guia de estilo es parte de la capa Invariante y no tiene tabla: la pone
    # quien encarga la escena.
    guia_de_estilo: str | None = None


class PeticionDeRecuperacion(_Esquema):
    entidades: list[Referencia] = []
    consulta: list[float] | None = None
    maximo: int = 12


class Pieza(_Esquema):
    capa: Capa
    fuente: str
    nivel: NivelDeCompresion | None = None
    texto: str


class Anticontexto(_Esquema):
    usos: list[UsoDeRecurso] = []
    entidades_presentadas: list[Referencia] = []
    hechos_vigentes: list[HechoCanonico] = []


class ContextoEnsamblado(_Esquema):
    escena_id: int
    piezas: list[Pieza]
    tokens_por_capa: dict[Capa, int]
    total: int
    degradadas: list[Capa]
    prompt: str


class PresupuestoDeclarado(_Esquema):
    """El reparto que declara `config/thresholds.yaml`, tal cual.

    Es la otra mitad de «consultar presupuesto y reparto resultante»: esto es lo
    que el sistema **tiene**, y `ContextoEnsamblado.tokens_por_capa` es lo que
    una escena concreta **gasto**. Sin las dos, un ensamblado que no cabe no se
    puede diagnosticar sin abrir el fichero.

    Las cifras no se copian a ningun documento: se leen de ahi y se sirven.
    """

    total: int
    por_capa: dict[Capa, int]
    margen: int
    orden_de_degradacion: list[Capa]
    intocables: list[Capa]


class FragmentoRecuperado(_Esquema):
    id: int
    escena_id: int
    texto: str
    nivel: NivelDeCompresion
    distancia: float


__all__ = [
    "Anticontexto",
    "ContextoEnsamblado",
    "Fragmento",
    "FragmentoRecuperado",
    "NuevoFragmento",
    "NuevoUso",
    "PeticionDeEnsamblado",
    "PeticionDeRecuperacion",
    "PresupuestoDeclarado",
    "Pieza",
    "Referencia",
]
