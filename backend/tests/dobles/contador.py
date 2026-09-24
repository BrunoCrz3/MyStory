"""Contador de tokens determinista: cuatro caracteres por token, más un recargo fijo por
petición opcional para simular la sobrecarga del proveedor."""

from __future__ import annotations

from app.commons.config import Rol
from app.commons.llm import Peticion
from tests.dobles.modelo import contar, tokens_de


class ContadorDeterminista:
    def __init__(self, recargo_por_peticion: int = 0) -> None:
        self.recargo = recargo_por_peticion
        self.textos_contados = 0

    async def contar_texto(self, rol: Rol, texto: str) -> int:
        self.textos_contados += 1
        return contar(texto) if texto else 0

    async def contar_peticion(self, peticion: Peticion) -> int:
        return tokens_de(peticion) + self.recargo
