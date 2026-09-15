"""Capa LLM: un unico Protocol y varios proveedores intercambiables.

Cambiar de proveedor afecta EXCLUSIVAMENTE a este paquete. Si un agente, un
validador o el orquestador necesitan cambios al cambiar de proveedor, la
abstraccion esta rota (BUILD_SPEC §24.1).
"""

from novela.llm.base import LLMClient, LLMRequest, LLMResponse
from novela.llm.router import Router, build_client

__all__ = ["LLMClient", "LLMRequest", "LLMResponse", "Router", "build_client"]
