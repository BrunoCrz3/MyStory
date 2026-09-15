"""Cliente Anthropic directo (BUILD_SPEC §6.3).

Reintentos con retroceso exponencial (1s, 2s, 4s), timeout de 120 s y registro
del coste en `observability/cost.py`. La clave NUNCA se escribe en logs ni en
`trace.jsonl`.
"""

from __future__ import annotations

import os
import time
from typing import Any

from novela.errors import ProviderError
from novela.llm.base import LLMResponse

TIMEOUT_SECONDS = 120.0
BACKOFF_SECONDS: tuple[float, ...] = (1.0, 2.0, 4.0)
ENV_VAR = "ANTHROPIC_API_KEY"


def _api_key() -> str:
    key = os.environ.get(ENV_VAR, "").strip()
    if not key:
        raise ProviderError(
            f"falta la variable de entorno {ENV_VAR}. Copia .env.example a .env y rellena "
            "la clave, o exporta la variable en tu shell."
        )
    return key


class AnthropicClient:
    """Implementacion del Protocol `LLMClient` sobre el SDK oficial."""

    def __init__(self, client: Any | None = None) -> None:
        if client is not None:
            self._client = client
            return
        try:
            import anthropic
        except ImportError as error:  # pragma: no cover - dependencia declarada en §2.2
            raise ProviderError("el paquete 'anthropic' no está instalado") from error
        self._client = anthropic.Anthropic(api_key=_api_key(), timeout=TIMEOUT_SECONDS)

    def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        temperature: float,
        max_tokens: int,
        seed: int | None = None,
        role: str = "unknown",
        chapter: int | None = None,
        json_schema: dict[str, object] | None = None,
    ) -> LLMResponse:
        last: Exception | None = None
        for delay in (*BACKOFF_SECONDS, None):
            started = time.monotonic()
            try:
                message = self._client.messages.create(
                    model=model,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as error:
                last = error
                if delay is None:
                    break
                time.sleep(delay)
                continue
            return _to_response(message, model, started)

        raise ProviderError(
            f"la llamada a Anthropic ha fallado tras {len(BACKOFF_SECONDS) + 1} intentos "
            f"(rol '{role}', modelo '{model}'): {last}"
        )


def _to_response(message: Any, model: str, started: float) -> LLMResponse:
    blocks = getattr(message, "content", []) or []
    text = "".join(getattr(block, "text", "") for block in blocks)
    usage = getattr(message, "usage", None)
    return LLMResponse(
        text=text,
        input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
        output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
        model=str(getattr(message, "model", model)),
        latency_ms=int((time.monotonic() - started) * 1000),
        json_mode="prompt",
    )
