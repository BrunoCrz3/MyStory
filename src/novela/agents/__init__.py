"""Agentes del runtime (BUILD_SPEC §7).

Cada agente tiene un unico metodo publico `run(...)`. Ninguno escribe en el
store: devuelven objetos y el orquestador persiste (§2.3).
"""

from novela.agents.base import AgentContext, JsonAgent, ProseAgent, extract_json, length_instruction

__all__ = [
    "AgentContext",
    "JsonAgent",
    "ProseAgent",
    "extract_json",
    "length_instruction",
]
