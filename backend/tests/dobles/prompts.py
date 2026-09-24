"""Doble del registro de prompts de Langfuse: guarda en memoria lo que se publica."""

from __future__ import annotations

from collections import defaultdict

from app.prompts.cargar import PromptCargado


class RegistroPromptsEnMemoria:
    def __init__(self) -> None:
        self.publicados: list[PromptCargado] = []
        self.etiquetas: dict[str, set[str]] = defaultdict(set)

    def existe(self, nombre: str, hash_git: str) -> bool:
        return hash_git in self.etiquetas[nombre]

    def publicar(self, prompt: PromptCargado) -> None:
        self.publicados.append(prompt)
        self.etiquetas[prompt.nombre].add(prompt.hash_git)
