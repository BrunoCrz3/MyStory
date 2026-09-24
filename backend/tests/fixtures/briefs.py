"""Briefs de prueba. Todos ficticios (RNF-17).

El de ejemplo es el `example` de `BriefNovela` en el contrato: una sola fuente, así que si el
contrato cambia su ejemplo, las pruebas lo siguen.
"""

from __future__ import annotations

import copy
from typing import Any

from tests.contrato.normalizar import cargar_contrato

_EJEMPLO: dict[str, Any] = cargar_contrato()["components"]["schemas"]["BriefNovela"]["example"]


def brief_ejemplo(**cambios: Any) -> dict[str, Any]:
    brief = copy.deepcopy(_EJEMPLO)
    for clave, valor in cambios.items():
        destino = brief
        partes = clave.split("__")
        for parte in partes[:-1]:
            destino = destino[parte]
        destino[partes[-1]] = valor
    return brief
