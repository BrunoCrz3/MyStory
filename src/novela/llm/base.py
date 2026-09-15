"""Contrato unico de la capa LLM (BUILD_SPEC §6.1)."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict


class LLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    latency_ms: int = 0
    # Solo lo rellenan los proveedores que informan de ello (OpenRouter, §24.5).
    cost_usd: float | None = None
    generation_id: str | None = None
    effective_provider: str | None = None
    json_mode: str | None = None


class LLMRequest(BaseModel):
    """Peticion normalizada. `role` y `chapter` son metadatos de trazado.

    Los proveedores reales los ignoran a efectos de red; el `FakeLLM` los usa
    para resolver la fixture y el trazador para etiquetar la llamada.
    """

    model_config = ConfigDict(extra="forbid")

    system: str
    user: str
    model: str
    temperature: float
    max_tokens: int
    seed: int | None = None
    role: str = "unknown"
    chapter: int | None = None
    json_schema: dict[str, object] | None = None


class LLMClient(Protocol):
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
    ) -> LLMResponse: ...
