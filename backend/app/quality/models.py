"""Capa 4 de la ontologia: calidad.

Tres clases con tabla —`Dimension de calidad`, `Informe de critica` y
`Defecto`—, que son las que `architecture.md` § Anatomia de una feature asigna a
`quality/`. La puntuacion por dimension no esta aqui: es la relacion entre dos
de ellas, como los puentes de la Capa 1, y vive en `schemas.py`.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

# Gravedad de un defecto. Los mismos tres valores que usa `Contradiccion` en la
# Capa 2: si en algun momento divergen, sera porque alguien lo decidio.
GRAVEDADES = ("baja", "media", "alta")

# Niveles de aplicacion de la Capa 4. El nivel decide el alcance del defecto.
NIVELES_LOCALES = frozenset({"Frase", "Escena"})


class AlcanceDelDefecto(StrEnum):
    """Un defecto local se corrige reescribiendo en sitio. Uno sistemico
    invalida la planificacion y obliga a replanificar.

    Distinguirlos determina la ruta de correccion y evita parchear sintomas de
    un problema estructural.
    """

    LOCAL = "local"
    SISTEMICO = "sistemico"


class Eje(StrEnum):
    """Los cuatro ejes de continuidad de RF-QUA-01, mas el especulativo.

    No son dimensiones: son la clasificacion de lo que el verificador contrasta
    contra el canon. Cada uno desemboca en la dimension que le corresponde.
    """

    FACTICA = "factica"
    TEMPORAL = "temporal"
    ESPACIAL = "espacial"
    EPISTEMICA = "epistemica"
    ESPECULATIVA = "especulativa"


class _Entidad(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    id: int


Entidad = _Entidad


class DimensionDeCalidad(_Entidad):
    nombre: str
    nivel: str
    medicion: str


class InformeDeCritica(_Entidad):
    escena_id: int
    version: int
    fase_de_medicion: bool
    escenas_aceptadas: int


class Defecto(_Entidad):
    informe_id: int
    dimension: str
    gravedad: str
    alcance: AlcanceDelDefecto
    eje: Eje | None = None
    localizacion: str | None = None
    descripcion: str
