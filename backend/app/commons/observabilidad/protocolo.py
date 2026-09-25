"""Costura con Langfuse: sesión por novela, traza por generación, span por rol y por tool,
score por validador (`architecture.md` § Observabilidad).

Los nombres de span son **cerrados**: los de `architecture.md` § Agentes más los puntos del
proceso. Un nombre fuera de la lista es un error, porque una traza con nombres inventados no
se puede comparar entre generaciones.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, Protocol

from app.commons.config import Rol
from app.commons.llm.protocolo import Peticion, Respuesta

AGENTE_DE_ROL: dict[Rol, str] = {
    "entrevistador": "interviewer",
    "planificador": "planner",
    "redactor": "writer",
    "judge": "judge",
    "editor": "editor",
    "extractor": "extractor",
}
TOOLS = frozenset({"consultar_story_bible", "extraer_hechos_texto_libre", "detectar_contradiccion"})
PUNTOS_DEL_PROCESO = frozenset(
    {
        "generacion",
        "capitulo",
        "hook_policy",
        "hook_capitulo",
        "rol_editor",
        "consolidar",
        "gate_publicacion",
        "lean",
        "publicar",
        "validar_brief",
        "export",
    }
)
NOMBRES_SPAN = frozenset(AGENTE_DE_ROL.values()) | TOOLS | PUNTOS_DEL_PROCESO


def validar_nombre_span(nombre: str) -> str:
    if nombre not in NOMBRES_SPAN:
        raise ValueError(f"span {nombre!r} fuera de la lista cerrada de architecture.md § Agentes")
    return nombre


@dataclass(frozen=True)
class ContextoTraza:
    """`traza_id` es el de Langfuse, o `None` si no hay Langfuse: nunca un id inventado."""

    traza_id: str | None
    url: str | None
    id_local: str


class Observacion(Protocol):
    def actualizar(self, *, salida: Any = None, metadata: dict[str, Any] | None = None) -> None: ...

    def registrar(self, respuesta: Respuesta) -> None: ...

    def error(self, error: BaseException) -> None: ...


class Trazador(Protocol):
    @property
    def degradado(self) -> bool: ...

    def traza(
        self, nombre: str, *, novel_id: str, metadata: dict[str, Any] | None = None
    ) -> AbstractContextManager[ContextoTraza]: ...

    def span(
        self, nombre: str, *, entrada: Any = None, metadata: dict[str, Any] | None = None
    ) -> AbstractContextManager[Observacion]: ...

    def generacion(self, peticion: Peticion) -> AbstractContextManager[Observacion]: ...

    def score(
        self,
        nombre: str,
        valor: float,
        *,
        comentario: str | None,
        traza_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...

    def cerrar(self) -> None: ...
