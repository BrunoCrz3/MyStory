"""La única implementación de producción de `ClienteModelo`: la API de Claude.

Toda llamada es asíncrona, con timeout explícito de configuración y **sin los reintentos
del SDK**: los reintentos son nuestros, con su propio contador (RF-PROC-09), y dos capas
de reintento esconderían cuántas veces se llamó de verdad.
"""

from __future__ import annotations

import json
import time
from typing import Any

import anthropic
import httpx2

from app.commons.config import Config
from app.commons.llm.protocolo import (
    ErrorModelo,
    FalloInfraestructura,
    Peticion,
    Recuento,
    Respuesta,
    SalidaInvalida,
    SalidaTruncada,
)

_REINTENTABLES = frozenset({408, 409, 429})


def _clasificar(error: Exception) -> ErrorModelo:
    if isinstance(error, anthropic.APIConnectionError):
        return FalloInfraestructura(f"conexión con el proveedor: {type(error).__name__}")
    if isinstance(error, anthropic.APIStatusError):
        if error.status_code in _REINTENTABLES or error.status_code >= 500:
            return FalloInfraestructura(f"el proveedor devolvió {error.status_code}")
        return ErrorModelo(f"el proveedor rechazó la petición ({error.status_code})")
    return ErrorModelo(f"fallo del cliente del modelo: {type(error).__name__}")


class ClienteAnthropic:
    def __init__(
        self,
        config: Config,
        *,
        api_key: str | None = None,
        http_client: httpx2.AsyncClient | None = None,
    ) -> None:
        self.config = config
        self.timeout_segundos = config.umbrales.orquestacion.timeout_llamada_segundos
        # Sin `api_key`, el SDK la resuelve del entorno (`ANTHROPIC_API_KEY`); nunca se
        # escribe en el repositorio ni en un log.
        self.sdk = anthropic.AsyncAnthropic(
            api_key=api_key,
            timeout=self.timeout_segundos,
            max_retries=0,
            http_client=http_client,
        )

    def _parametros(self, peticion: Peticion) -> dict[str, Any]:
        rol = self.config.modelos.roles.de(peticion.rol)
        output_config: dict[str, Any] = {"effort": rol.effort}
        if peticion.esquema_salida is not None:
            output_config["format"] = {"type": "json_schema", "schema": peticion.esquema_salida}
        return {
            "model": rol.id,
            "system": peticion.system,
            "messages": [{"role": m.role, "content": m.contenido} for m in peticion.mensajes],
            "output_config": output_config,
        }

    async def contar_tokens(self, peticion: Peticion) -> Recuento:
        try:
            resultado = await self.sdk.messages.count_tokens(**self._parametros(peticion))
        except anthropic.AnthropicError as e:
            raise _clasificar(e) from e
        return Recuento.de(
            peticion,
            tokens_entrada=resultado.input_tokens,
            max_tokens=self.config.max_tokens(peticion.rol),
        )

    async def generar(self, peticion: Peticion, recuento: Recuento) -> Respuesta:
        if not recuento.corresponde_a(peticion):
            raise ValueError("el recuento no corresponde a esta petición: hay que contar antes")
        parametros = self._parametros(peticion)
        inicio = time.monotonic()
        try:
            mensaje = await self.sdk.messages.create(
                max_tokens=recuento.max_tokens,
                thinking={"type": "adaptive"},
                **parametros,
            )
        except anthropic.AnthropicError as e:
            raise _clasificar(e) from e
        latencia = time.monotonic() - inicio

        if mensaje.stop_reason == "max_tokens":
            raise SalidaTruncada(
                f"{peticion.rol}: la respuesta llegó a max_tokens ({recuento.max_tokens})"
            )
        if mensaje.stop_reason == "refusal":
            raise ErrorModelo(f"{peticion.rol}: el modelo rechazó la petición")

        texto = "".join(b.text for b in mensaje.content if b.type == "text")
        datos: dict[str, Any] | None = None
        if peticion.esquema_salida is not None:
            try:
                cargado = json.loads(texto)
            except json.JSONDecodeError as e:
                raise SalidaInvalida(f"{peticion.rol}: la salida no es JSON") from e
            if not isinstance(cargado, dict):
                raise SalidaInvalida(f"{peticion.rol}: la salida no es un objeto JSON")
            datos = cargado

        uso = mensaje.usage
        detalles = uso.output_tokens_details
        return Respuesta(
            modelo=parametros["model"],
            texto=texto,
            datos=datos,
            stop_reason=mensaje.stop_reason,
            tokens_entrada=uso.input_tokens,
            tokens_salida=uso.output_tokens,
            tokens_razonamiento=detalles.thinking_tokens if detalles is not None else None,
            coste_usd=self.config.coste_usd(
                parametros["model"], uso.input_tokens, uso.output_tokens
            ),
            latencia_s=latencia,
        )
