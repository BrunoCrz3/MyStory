"""Carga los prompts por rol y la skill de runtime, con el hash de git del fichero usado.

El hash se calcula sobre **el contenido realmente leído**, como lo haría `git hash-object`,
y es lo que se registra en el span (TO-024): si la versión publicada en Langfuse y el fichero
local discrepan, la discrepancia se ve. Los finales de línea se normalizan a LF porque el
repositorio guarda LF (`.gitattributes`), así que en Windows el hash coincide igual.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from app.commons.config import Rol

DIRECTORIO_PROMPTS = Path(__file__).resolve().parent
DIRECTORIO_SKILLS = DIRECTORIO_PROMPTS.parent / "skills"

PROMPT_DE_ROL: dict[Rol, str] = {
    "entrevistador": "interviewer",
    "planificador": "planner",
    "redactor": "writer",
    "judge": "judge",
    "editor": "editor",
    "extractor": "extractor",
}
# La capa Invariante se compone por rol (TO-021): los tres que escriben o planifican la
# prosa cargan la skill; el entrevistador, el judge y el extractor, no.
SKILLS_DE_ROL: dict[Rol, tuple[str, ...]] = {
    "entrevistador": (),
    "planificador": ("personalizacion-natural",),
    "redactor": ("personalizacion-natural",),
    "judge": (),
    "editor": ("personalizacion-natural",),
    "extractor": (),
}


@dataclass(frozen=True)
class PromptCargado:
    nombre: str
    ruta: Path
    texto: str
    hash_git: str


def hash_git(contenido: bytes) -> str:
    normalizado = contenido.replace(b"\r\n", b"\n")
    cabecera = f"blob {len(normalizado)}\0".encode()
    return hashlib.sha1(cabecera + normalizado, usedforsecurity=False).hexdigest()


def _cargar(nombre: str, ruta: Path) -> PromptCargado:
    crudo = ruta.read_bytes()
    return PromptCargado(
        nombre=nombre,
        ruta=ruta,
        texto=crudo.decode("utf-8").replace("\r\n", "\n"),
        hash_git=hash_git(crudo),
    )


@cache
def cargar_prompt(nombre: str) -> PromptCargado:
    return _cargar(nombre, DIRECTORIO_PROMPTS / f"{nombre}.md")


@cache
def cargar_skill(nombre: str) -> PromptCargado:
    return _cargar(nombre, DIRECTORIO_SKILLS / nombre / "SKILL.md")


def prompt_de(rol: Rol) -> PromptCargado:
    return cargar_prompt(PROMPT_DE_ROL[rol])


def skills_de(rol: Rol) -> list[PromptCargado]:
    return [cargar_skill(s) for s in SKILLS_DE_ROL[rol]]
