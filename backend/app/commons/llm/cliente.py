"""Cliente del modelo (RI-06, A-02, A-35).

Tres cosas que no son negociables y que estan aqui para que ninguna feature las
tenga que recordar:

- **Asincrono y con timeout explicito.** El trabajo largo corre dentro de este
  mismo proceso; un timeout implicito es un cuelgue esperando a ocurrir.
- **Se cuenta antes de llamar.** Un ensamblado que no cabe falla en voz alta y
  no se trunca en silencio: truncar produce una escena generada sin el estado
  que la condiciona, indistinguible de una buena hasta que alguien encuentra la
  contradiccion — o hasta que no la encuentra.
- **Ninguna cifra vive aqui.** La ventana, el margen de respuesta y el timeout
  se leen de `config/thresholds.yaml` (RNF-14).

`commons/` no sabe que es una escena: este cliente habla de mensajes y tokens,
no de briefs ni de canon.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from anthropic import (
    APIConnectionError,
    APIStatusError,
    AsyncAnthropic,
    RateLimitError,
    omit,
)

from app.commons.config import Umbrales
from app.commons.errores import PresupuestoExcedido
from app.commons.tokens.contador import ContadorDeTokens


@dataclass(frozen=True)
class RespuestaDelModelo:
    texto: str
    modelo: str
    tokens_de_entrada: int
    tokens_de_salida: int


# Primer codigo de estado que es del proveedor y no de la peticion. Por debajo
# de aqui el problema es nuestro, y reintentar lo repetiria igual.
PRIMER_ERROR_DEL_SERVIDOR = 500


def es_reintentable(error: BaseException) -> bool:
    """Si volver a pedir lo mismo puede salir bien (RI-07).

    Saber que errores son transitorios es del proveedor, asi que vive aqui y no
    en `process/`: la feature que orquesta no tiene por que conocer el SDK.

    Un 4xx no entra. Un prompt que no cabe, una credencial mala o un modelo que
    no existe no se arreglan esperando, y reintentarlos es gastar el tope de
    intentos en algo que va a fallar igual.
    """
    if isinstance(error, RateLimitError | APIConnectionError):
        return True
    if isinstance(error, APIStatusError):
        return error.status_code >= PRIMER_ERROR_DEL_SERVIDOR
    return False


class Generador(Protocol):
    """Lo unico que `process/` necesita saber del proveedor.

    Existe para que la puerta que registra cada generacion dependa del contrato
    y no de la clase concreta: `commons/` no sabe que es una escena, y `process/`
    no tiene por que saber que hay un SDK detras.
    """

    async def generar(
        self, mensajes: list[dict[str, Any]], sistema: str | None = None
    ) -> RespuestaDelModelo: ...


class ClienteDelModelo:
    def __init__(self, umbrales: Umbrales, cliente: AsyncAnthropic | None = None) -> None:
        self._umbrales = umbrales
        self._cliente = cliente or AsyncAnthropic()
        self._contador = ContadorDeTokens(
            self._cliente,
            modelo=umbrales.modelo.id,
            timeout_segundos=umbrales.modelo.timeout_segundos,
        )

    @property
    def contador(self) -> ContadorDeTokens:
        return self._contador

    async def generar(
        self, mensajes: list[dict[str, Any]], sistema: str | None = None
    ) -> RespuestaDelModelo:
        entrada = await self._contador.contar(mensajes, sistema)
        ventana = self._umbrales.contexto.total
        if entrada > ventana:
            raise PresupuestoExcedido(
                f"el prompt ocupa {entrada} tokens y la ventana declarada es {ventana}: "
                "comprime el ensamblado, no la ventana"
            )

        respuesta = await self._cliente.messages.create(
            model=self._umbrales.modelo.id,
            max_tokens=self._umbrales.contexto.capas.margen,
            messages=mensajes,  # type: ignore[arg-type]
            system=sistema if sistema is not None else omit,
            timeout=self._umbrales.modelo.timeout_segundos,
        )

        texto = "".join(bloque.text for bloque in respuesta.content if bloque.type == "text")
        return RespuestaDelModelo(
            texto=texto,
            modelo=respuesta.model,
            tokens_de_entrada=respuesta.usage.input_tokens,
            tokens_de_salida=respuesta.usage.output_tokens,
        )
