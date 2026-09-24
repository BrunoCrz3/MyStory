# `sync` no se reexporta: es también el comando `python -m app.prompts.sync`.
from app.prompts.cargar import (
    PROMPT_DE_ROL,
    SKILLS_DE_ROL,
    PromptCargado,
    cargar_prompt,
    cargar_skill,
    prompt_de,
    skills_de,
)

__all__ = [
    "PROMPT_DE_ROL",
    "SKILLS_DE_ROL",
    "PromptCargado",
    "cargar_prompt",
    "cargar_skill",
    "prompt_de",
    "skills_de",
]
