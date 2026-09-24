"""Recursos de la instancia que crea el `lifespan` y usan las rutas y el worker."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.commons.config import Config
from app.commons.db import BaseDatos
from app.commons.llm.llamar import LlamadorModelo
from app.commons.llm.pool import PoolEnVuelo
from app.commons.observabilidad import Trazador


@dataclass
class Recursos:
    config: Config
    db: BaseDatos
    pool: PoolEnVuelo
    trazador: Trazador
    llamador: LlamadorModelo


def recursos(request: Request) -> Recursos:
    """Dependencia de FastAPI: los recursos de la instancia en marcha."""
    valor: Recursos = request.app.state.recursos
    return valor
