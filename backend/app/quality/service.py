"""Servicio de calidad: los validadores del hook de capítulo y del rol editor.

El hook de capítulo corre solo validadores programáticos: no llama al modelo y por eso va
fuera del pool en vuelo (`architecture.md` § Paralelo y serie).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.commons.config import Config
from app.quality.models import Defecto, ResultadoValidador
from app.quality.validadores.basicos import longitud, nombres_exactos

__all__ = ["Defecto", "EntradaHookCapitulo", "ResultadoValidador", "hook_capitulo"]


class EntradaHookCapitulo(BaseModel):
    """Lo que el hook de capítulo necesita para validar un borrador."""

    model_config = ConfigDict(frozen=True)

    titulo: str
    texto: str
    nombres: list[str]


def hook_capitulo(config: Config, entrada: EntradaHookCapitulo) -> list[ResultadoValidador]:
    return [
        longitud(config, entrada.texto),
        nombres_exactos(entrada.texto, entrada.nombres),
    ]
