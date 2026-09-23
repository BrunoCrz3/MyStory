"""Contratos de `findings/` (RI-02)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.findings.models import (
    EstadoDeHallazgo,
    FuenteDelHallazgo,
    Hallazgo,
    TipoDeHallazgo,
)


class _Esquema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Candidatura(_Esquema):
    """Una propuesta que no sale del detector determinista.

    Es la via por la que el `extractor` deja lo que leyo en la escena. No hace
    falta confiar en ella: **entra como `propuesto` igual que todo lo demas**, y
    esa es justamente la tercera regla de la resistencia a inyeccion. Un texto
    que lograra colar una afirmacion la deja aqui y muere aqui salvo que el
    autor la adopte.
    """

    tipo: TipoDeHallazgo
    texto: str
    confianza: float | None = None


class PeticionDeExtraccion(_Esquema):
    """`extraer-hallazgos`. Corre **despues** de consolidar, nunca antes.

    El `texto` lo trae quien llama, igual que `PeticionDeCritica` en `quality/`:
    `findings/` no es dueno de la prosa. La memoria episodica --las escenas
    aceptadas en su forma literal-- es de la Capa 3, y la semantica, de la 2.
    Ir a buscarla desde aqui ataria esta feature a donde vive hoy el texto.

    Lo que no se delega es **cuando** se puede extraer: la version tiene que
    estar consolidada, y eso lo comprueba el servicio contra el canon.
    """

    version: int
    texto: str
    candidaturas: list[Candidatura] = []
    registro_id: int | None = None


class ResultadoDeExtraccion(_Esquema):
    extraccion_id: int
    escena_id: int
    version: int
    hallazgos: list[Hallazgo]


class DecisionDelAutor(_Esquema):
    """La firma del autor sobre un hallazgo.

    `destino` es el estado al que lo mueve, y tiene que ser una arista del ciclo
    de vida. Las cuatro columnas de adopcion dicen **como que** se adopta: sin
    ninguna, un hallazgo `adoptado` seria una nota al margen.
    """

    destino: EstadoDeHallazgo
    hecho_id: int | None = None
    promesa_id: int | None = None
    motivo_id: int | None = None
    personaje_id: int | None = None


__all__ = [
    "Candidatura",
    "DecisionDelAutor",
    "EstadoDeHallazgo",
    "FuenteDelHallazgo",
    "Hallazgo",
    "PeticionDeExtraccion",
    "ResultadoDeExtraccion",
    "TipoDeHallazgo",
]
