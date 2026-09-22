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
from typing import Any

from anthropic import AsyncAnthropic, omit

from app.commons.config import Umbrales
from app.commons.errores import PresupuestoExcedido
from app.commons.tokens.contador import ContadorDeTokens


@dataclass(frozen=True)
class RespuestaDelModelo:
    texto: str
    modelo: str
    tokens_de_entrada: int
    tokens_de_salida: int


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
