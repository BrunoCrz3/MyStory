"""Contador de tokens (A-02, A-09, RF-CTX-03).

El recuento con el que se decide tiene que ser el que aplica el proveedor. Por
eso esto no estima con un tokenizador ajeno —undercuenta, y el prompt cabe en la
prueba y no en la ventana—: pregunta a la misma API que luego recibe el prompt.

La cuenta va **antes** de llamar al modelo, nunca despues. Contar despues es
contar el gasto, no decidir.
"""

from __future__ import annotations

from typing import Any

from anthropic import AsyncAnthropic, omit


class ContadorDeTokens:
    def __init__(self, cliente: AsyncAnthropic, modelo: str, timeout_segundos: float) -> None:
        self._cliente = cliente
        self._modelo = modelo
        self._timeout_segundos = timeout_segundos

    async def contar(self, mensajes: list[dict[str, Any]], sistema: str | None = None) -> int:
        respuesta = await self._cliente.messages.count_tokens(
            model=self._modelo,
            messages=mensajes,  # type: ignore[arg-type]
            system=sistema if sistema is not None else omit,
            timeout=self._timeout_segundos,
        )
        return respuesta.input_tokens
