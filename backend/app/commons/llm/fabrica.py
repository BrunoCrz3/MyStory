"""Elige la implementación de `ClienteModelo` según `proveedor` en `config/models.yaml`."""

from __future__ import annotations

from app.commons.config import Config
from app.commons.llm.claude_code import ClienteClaudeCode
from app.commons.llm.protocolo import ClienteModelo
from app.commons.llm.proveedor import ClienteAnthropic


def crear_cliente(config: Config) -> ClienteModelo:
    if config.modelos.proveedor == "claude_code":
        return ClienteClaudeCode(config)
    return ClienteAnthropic(config)
