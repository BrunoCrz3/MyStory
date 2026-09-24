"""Publica los prompts del repositorio en Langfuse, una versión por hash de git (TO-024).

    uv run --env-file ../.env python -m app.prompts.sync

**Idempotente por hash**: un prompt cuyo hash ya está publicado no se vuelve a publicar, o
cada ejecución crearía una versión idéntica y el historial dejaría de significar nada.
**Corre en CI y a mano antes de un eval, nunca al arrancar**: el arranque no depende de la
red, y sin red el backend usa el fichero local.
"""

from __future__ import annotations

import os
import sys
from typing import Protocol

from app.prompts.cargar import PROMPT_DE_ROL, PromptCargado, cargar_prompt

# Langfuse rechaza etiquetas de más de 36 caracteres. `git-` y los 32 primeros caracteres del
# hash caben justo, y 128 bits siguen identificando la versión sin colisión práctica.
LIMITE_ETIQUETA_LANGFUSE = 36
_PREFIJO = "git-"


def etiqueta_git(hash_git: str) -> str:
    return _PREFIJO + hash_git[: LIMITE_ETIQUETA_LANGFUSE - len(_PREFIJO)]


class RegistroPrompts(Protocol):
    def existe(self, nombre: str, hash_git: str) -> bool: ...

    def publicar(self, prompt: PromptCargado) -> None: ...


class RegistroLangfuse:
    """El registro de producción: la gestión de prompts de Langfuse, con el hash de git como
    etiqueta de cada versión."""

    def __init__(self) -> None:
        from langfuse import Langfuse

        self._cliente = Langfuse(
            public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
            secret_key=os.environ["LANGFUSE_SECRET_KEY"],
            host=os.environ.get("LANGFUSE_HOST") or None,
        )

    def existe(self, nombre: str, hash_git: str) -> bool:
        try:
            self._cliente.get_prompt(nombre, label=etiqueta_git(hash_git), cache_ttl_seconds=0)
        except Exception:
            return False
        return True

    def publicar(self, prompt: PromptCargado) -> None:
        self._cliente.create_prompt(
            name=prompt.nombre,
            prompt=prompt.texto,
            type="text",
            labels=[etiqueta_git(prompt.hash_git)],
            commit_message=f"git {prompt.hash_git}",
        )

    def cerrar(self) -> None:
        self._cliente.flush()


def sincronizar(registro: RegistroPrompts) -> list[PromptCargado]:
    """Publica los prompts cuyo hash no esté ya. Devuelve los que publicó."""
    publicados = []
    for nombre in sorted(set(PROMPT_DE_ROL.values())):
        prompt = cargar_prompt(nombre)
        if not registro.existe(prompt.nombre, prompt.hash_git):
            registro.publicar(prompt)
            publicados.append(prompt)
    return publicados


def main() -> int:
    if not (os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")):
        print("faltan LANGFUSE_PUBLIC_KEY y LANGFUSE_SECRET_KEY en el entorno")
        return 2
    registro = RegistroLangfuse()
    try:
        publicados = sincronizar(registro)
    finally:
        registro.cerrar()
    for p in publicados:
        print(f"publicado {p.nombre} {etiqueta_git(p.hash_git)}")
    print(f"{len(publicados)} prompts publicados; el resto ya estaba")
    return 0


if __name__ == "__main__":
    sys.exit(main())
