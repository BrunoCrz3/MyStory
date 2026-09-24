"""Doble del modelo para la suite normal. Vive en `tests/`, nunca en `app/` (TO-034).

Devuelve salidas guionizadas por rol y cuenta tokens de forma determinista: cuatro
caracteres por token, que es lo bastante cerca del recuento real como para que los
presupuestos se comporten igual y lo bastante simple como para calcularlo a mano en una
prueba.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from app.commons.config import Config, Rol
from app.commons.llm import Peticion, Recuento, Respuesta

Salida = dict[str, Any] | str | Exception
Guion = Salida | Callable[[Peticion], Salida]


def contar(texto: str) -> int:
    return max(1, len(texto) // 4)


def tokens_de(peticion: Peticion) -> int:
    partes = [peticion.system, *(m.contenido for m in peticion.mensajes)]
    if peticion.esquema_salida is not None:
        partes.append(json.dumps(peticion.esquema_salida))
    return contar("\n".join(partes))


class ModeloGuionizado:
    def __init__(
        self,
        config: Config,
        salidas: dict[Rol, list[Guion]] | None = None,
        por_defecto: dict[Rol, Callable[[Peticion], Salida]] | None = None,
    ) -> None:
        self.config = config
        self.salidas: dict[Rol, list[Guion]] = {k: list(v) for k, v in (salidas or {}).items()}
        self.por_defecto = por_defecto or {}
        self.peticiones: list[Peticion] = []
        self.recuentos: list[Recuento] = []
        self.llamadas: dict[str, int] = defaultdict(int)

    def encolar(self, rol: Rol, *guiones: Guion) -> None:
        self.salidas.setdefault(rol, []).extend(guiones)

    async def contar_tokens(self, peticion: Peticion) -> Recuento:
        recuento = Recuento.de(
            peticion,
            tokens_entrada=tokens_de(peticion),
            max_tokens=self.config.max_tokens(peticion.rol),
        )
        self.recuentos.append(recuento)
        return recuento

    async def generar(self, peticion: Peticion, recuento: Recuento) -> Respuesta:
        if not recuento.corresponde_a(peticion):
            raise ValueError("el recuento no corresponde a esta petición: hay que contar antes")
        self.peticiones.append(peticion)
        self.llamadas[peticion.rol] += 1

        cola = self.salidas.get(peticion.rol)
        guion: Guion
        if cola:
            guion = cola.pop(0)
        elif peticion.rol in self.por_defecto:
            guion = self.por_defecto[peticion.rol]
        else:
            raise AssertionError(f"el doble no tiene guion para el rol {peticion.rol}")
        salida = guion(peticion) if callable(guion) else guion
        if isinstance(salida, Exception):
            raise salida

        datos: dict[str, Any] | None
        if isinstance(salida, dict):
            texto, datos = json.dumps(salida, ensure_ascii=False), salida
        else:
            texto = salida
            datos = json.loads(salida) if peticion.esquema_salida is not None else None

        modelo = self.config.modelos.roles.de(peticion.rol).id
        salida_tokens = contar(texto)
        return Respuesta(
            modelo=modelo,
            texto=texto,
            datos=datos,
            stop_reason="end_turn",
            tokens_entrada=recuento.tokens_entrada,
            tokens_salida=salida_tokens,
            tokens_razonamiento=0,
            coste_usd=self.config.coste_usd(modelo, recuento.tokens_entrada, salida_tokens),
            latencia_s=0.0,
        )
