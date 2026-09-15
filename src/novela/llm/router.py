"""Seleccion de cliente y de modelo por rol de agente (BUILD_SPEC §6, §24.2)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from novela.config import Config, ModelCfg
from novela.errors import ProviderError
from novela.llm.base import LLMClient, LLMResponse


@dataclass(frozen=True)
class Router:
    """Traduce un rol de agente en (cliente, modelo, temperatura, max_tokens)."""

    client: LLMClient
    config: Config

    def model_for(self, role: str) -> ModelCfg:
        return self.config.model_for(role)

    def complete(
        self,
        *,
        role: str,
        system: str,
        user: str,
        chapter: int | None = None,
        json_schema: dict[str, object] | None = None,
    ) -> LLMResponse:
        model = self.model_for(role)
        return self.client.complete(
            system=system,
            user=user,
            model=model.name,
            temperature=model.temperature,
            max_tokens=model.max_tokens,
            seed=self.config.project.seed,
            role=role,
            chapter=chapter,
            json_schema=json_schema,
        )


def build_client(config: Config, *, fixtures_dir: Path | None = None) -> LLMClient:
    """Instancia el proveedor declarado en `llm.provider`. No hay ningun otro sitio."""
    provider = config.llm.provider
    if provider == "fake":
        from novela.llm.fake import FakeLLM

        if fixtures_dir is None:
            raise ProviderError(
                "el proveedor 'fake' necesita un directorio de fixtures: "
                "pasa fixtures_dir al construir el cliente"
            )
        return FakeLLM(fixtures_dir)
    if provider == "anthropic":
        from novela.llm.anthropic_client import AnthropicClient

        return AnthropicClient()
    if provider == "openrouter":
        from novela.llm.openrouter_client import OpenRouterClient

        return OpenRouterClient(config.llm.openrouter)
    raise ProviderError(f"proveedor LLM desconocido: '{provider}'")
