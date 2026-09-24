"""Doble del subproceso del CLI de Claude Code (I-04). Vive en `tests/`, nunca en `app/`.

Guarda cómo se le llamó —orden, entrada, carpeta y entorno— y, **en el momento de la
llamada**, qué había en la carpeta de trabajo: después ya se habrá borrado. Responde con el
JSON que el CLI devuelve con `--output-format json`.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import anyio

from app.commons.llm.claude_code import ResultadoProceso


def resultado_cli(
    *,
    result: str = "",
    structured_output: dict[str, Any] | None = None,
    is_error: bool = False,
    api_error_status: int | None = None,
    terminal_reason: str = "completed",
    stop_reason: str = "end_turn",
    entrada: int = 10,
    cache: int = 2600,
    salida: int = 500,
    razonamiento: int = 120,
    coste: float | None = 0.05,
) -> dict[str, Any]:
    datos: dict[str, Any] = {
        "type": "result",
        "subtype": "success",
        "is_error": is_error,
        "api_error_status": api_error_status,
        "terminal_reason": terminal_reason,
        "stop_reason": stop_reason,
        "result": result,
        "usage": {
            "input_tokens": entrada,
            "cache_creation_input_tokens": cache,
            "cache_read_input_tokens": 0,
            "output_tokens": salida,
            "output_tokens_details": {"thinking_tokens": razonamiento},
        },
        "total_cost_usd": coste,
    }
    if structured_output is not None:
        datos["structured_output"] = structured_output
    return datos


@dataclass
class Llamada:
    orden: list[str]
    entrada: bytes
    cwd: Path
    env: dict[str, str]
    contenido_cwd: list[str]
    ficheros_orden: dict[str, str]


Respuesta = dict[str, Any] | ResultadoProceso | Callable[[Llamada], Any]


@dataclass
class LanzadorGuionizado:
    respuestas: list[Respuesta] = field(default_factory=list)
    llamadas: list[Llamada] = field(default_factory=list)
    retardo_s: float = 0.0

    async def __call__(
        self, orden: Sequence[str], *, entrada: bytes, cwd: Path, env: Mapping[str, str]
    ) -> ResultadoProceso:
        # Lo que el CLI podría leer por las rutas de su orden (el system va en un fichero).
        ficheros = {
            a: Path(a).read_text(encoding="utf-8")
            for a in orden
            if len(a) < 260 and Path(a).is_file() and a != orden[0]
        }
        llamada = Llamada(
            orden=list(orden),
            entrada=entrada,
            cwd=cwd,
            env=dict(env),
            contenido_cwd=sorted(p.name for p in cwd.iterdir()),
            ficheros_orden=ficheros,
        )
        self.llamadas.append(llamada)
        if self.retardo_s:
            await anyio.sleep(self.retardo_s)
        respuesta = self.respuestas.pop(0) if self.respuestas else resultado_cli(result="ok")
        if callable(respuesta):
            respuesta = respuesta(llamada)
        if isinstance(respuesta, ResultadoProceso):
            return respuesta
        return ResultadoProceso(
            codigo=1 if respuesta.get("is_error") else 0,
            salida=json.dumps(respuesta).encode("utf-8"),
            errores=b"",
        )
