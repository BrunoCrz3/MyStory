"""Costura con el proveedor: un `Protocol` con una sola implementación de producción.

El doble vive en `tests/dobles/` y se inyecta desde fuera (TO-034). Aquí no hay ninguno.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict

from app.commons.config import Rol


class Mensaje(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: Literal["user", "assistant"]
    contenido: str


class Peticion(BaseModel):
    """Todo lo que se manda al modelo en una llamada. Inmutable: se cuenta y se envía la
    misma."""

    model_config = ConfigDict(frozen=True)

    rol: Rol
    system: str
    mensajes: list[Mensaje]
    esquema_salida: dict[str, Any] | None = None
    prompt: str
    hash_prompt: str

    def huella(self) -> str:
        crudo = json.dumps(self.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(crudo.encode("utf-8")).hexdigest()


class Recuento(BaseModel):
    """Resultado de contar una petición **antes** de enviarla (RF-CTX-02).

    Va atado a la huella de la petición: un recuento de otra petición no vale para generar.
    """

    model_config = ConfigDict(frozen=True)

    huella: str
    tokens_entrada: int
    max_tokens: int

    @classmethod
    def de(cls, peticion: Peticion, *, tokens_entrada: int, max_tokens: int) -> Recuento:
        return cls(huella=peticion.huella(), tokens_entrada=tokens_entrada, max_tokens=max_tokens)

    @property
    def estimacion(self) -> int:
        """Lo que ocupa la llamada en el pool: entrada más la reserva de salida."""
        return self.tokens_entrada + self.max_tokens

    def corresponde_a(self, peticion: Peticion) -> bool:
        return self.huella == peticion.huella()


class Respuesta(BaseModel):
    model_config = ConfigDict(frozen=True)

    modelo: str
    texto: str
    datos: dict[str, Any] | None
    stop_reason: str | None
    tokens_entrada: int
    tokens_salida: int
    tokens_razonamiento: int | None
    coste_usd: float
    latencia_s: float


class ErrorModelo(RuntimeError):
    """La llamada falló por algo que reintentar no arregla (petición inválida, rechazo)."""


class FalloInfraestructura(ErrorModelo):
    """429, 5xx, timeout o red. Se reintenta con su propio contador (RF-PROC-09)."""


class SalidaTruncada(ErrorModelo):
    """La respuesta llegó a `max_tokens`. No se acepta a medias."""


class SalidaInvalida(ErrorModelo):
    """La salida no es el JSON que pedía el schema. Lo registra `schema_valido`."""


class ClienteModelo(Protocol):
    async def contar_tokens(self, peticion: Peticion) -> Recuento: ...

    async def generar(self, peticion: Peticion, recuento: Recuento) -> Respuesta: ...
