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
