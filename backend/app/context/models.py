"""Capa 3 de la ontologia: contexto y memoria.

Aqui no hay clases de la ontologia con tabla propia, y es deliberado.
`architecture.md` § Anatomia de una feature lo dice: las tres memorias
—episodica, semantica, procedural— son **la lectura por tipo** de lo que ya esta
en `data/novel.db`, y `Ventana efectiva` es una propiedad medida del modelo, no
un dato que se persista. Ninguna de las tres lleva `models.py`.

Lo que si vive aqui son las piezas que `context/` posee segun esa misma tabla:
el reparto por capas, la jerarquia de compresion y el registro de uso del que
sale el anticontexto.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Capa(StrEnum):
    """Las siete capas del diagrama «Ensamblado del contexto», mas el margen.

    El orden es el de la tabla, no el de degradacion: aquel vive en
    `config/thresholds.yaml`, bajo `contexto.degradacion`.
    """

    INVARIANTE = "invariante"
    ESTRUCTURAL = "estructural"
    ESTADO = "estado"
    LOCAL = "local"
    RECUPERADO = "recuperado"
    ESTILO = "estilo"
    ANTICONTEXTO = "anticontexto"
    MARGEN = "margen"


class NivelDeCompresion(StrEnum):
    """Lo lejano entra comprimido y lo cercano literal.

    Comprimir es bajar de resolucion, no recortar por la mitad: perder una
    escena entera cambia lo que el modelo sabe; resumirla solo cambia cuanto
    detalle tiene.
    """

    RESUMEN_DE_ACTO = "resumen_de_acto"
    RESUMEN_DE_CAPITULO = "resumen_de_capitulo"
    RESUMEN_DE_ESCENA = "resumen_de_escena"
    ESCENA_LITERAL = "escena_literal"


class TipoDeUso(StrEnum):
    METAFORA = "metafora"
    CLICHE_VETADO = "cliche_vetado"
    REVELACION_PROHIBIDA = "revelacion_prohibida"


class _Entidad(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    id: int


Entidad = _Entidad


class Fragmento(_Entidad):
    escena_id: int
    texto: str
    nivel: NivelDeCompresion
    embedding_model: str
    embedding_version: str


class UsoDeRecurso(_Entidad):
    escena_id: int
    tipo: TipoDeUso
    texto: str
