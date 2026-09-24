"""Ayudas para que Pydantic genere las formas exactas del contrato OpenAPI.

El contrato distingue dos opcionales que Python escribe igual:

- **opcional nulable** — `type: [string, 'null']`: el campo puede faltar o valer `null`. Es
  lo que Pydantic genera para `X | None = None`, y no necesita ayuda.
- **opcional sin nulo** — `type: string`, fuera de `required`: el campo puede faltar pero
  no valer `null`. Es `opcional()`: el tipo en Python sigue siendo `X | None` para poder
  omitirlo, y al serializar el `None` se omite.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field


def _sin_nulo(extra: dict[str, Any]) -> Any:
    def ajustar(schema: dict[str, Any]) -> None:
        alternativas = schema.pop("anyOf", None)
        if alternativas is not None:
            otras = [a for a in alternativas if a != {"type": "null"}]
            if len(otras) != 1:
                raise TypeError(f"opcional() espera X | None, no {alternativas!r}")
            schema.update(otras[0])
        schema.pop("default", None)
        schema.update(extra)

    return ajustar


def opcional(**extra: Any) -> Any:
    """Campo que puede faltar y no puede ser `null` en el contrato."""
    return Field(default=None, json_schema_extra=_sin_nulo(extra))


def sin_nulo(**extra: Any) -> Any:
    """`json_schema_extra` para un campo con valor por defecto que no es `None`."""
    return _sin_nulo(extra)
