"""JSON Schema estricto para la salida estructurada, a partir de un modelo Pydantic.

La salida estructurada del proveedor admite un subconjunto de JSON Schema y exige objetos
cerrados. Aquí se resuelven las referencias, se cierran los objetos, se marcan todas las
propiedades como obligatorias y se quitan las palabras clave que no admite —longitudes,
rangos, títulos—. **Lo quitado no se pierde**: la respuesta se valida después contra el mismo
modelo Pydantic, y esa validación es el validador `schema_valido`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

_CONSERVAR = frozenset(
    {
        "type",
        "properties",
        "required",
        "items",
        "enum",
        "additionalProperties",
        "description",
        "anyOf",
        "const",
    }
)


def _limpiar(nodo: Any, definiciones: dict[str, Any]) -> Any:
    if isinstance(nodo, list):
        return [_limpiar(v, definiciones) for v in nodo]
    if not isinstance(nodo, dict):
        return nodo
    if "$ref" in nodo:
        nombre = nodo["$ref"].rsplit("/", 1)[-1]
        return _limpiar(definiciones[nombre], definiciones)
    limpio: dict[str, Any] = {}
    for clave, valor in nodo.items():
        if clave not in _CONSERVAR:
            continue
        if clave == "properties":
            limpio[clave] = {k: _limpiar(v, definiciones) for k, v in valor.items()}
        else:
            limpio[clave] = _limpiar(valor, definiciones)
    if limpio.get("type") == "object":
        limpio["additionalProperties"] = False
        limpio["required"] = list(limpio.get("properties", {}))
    return limpio


def esquema_de_salida(modelo: type[BaseModel]) -> dict[str, Any]:
    crudo = modelo.model_json_schema()
    esquema: dict[str, Any] = _limpiar(crudo, crudo.get("$defs", {}))
    return esquema
