"""Excepciones de dominio, una por `type` del catálogo cerrado (spec § 4.3).

Un servicio lanza una de estas y el handler central la traduce a `problem+json`. Ningún
servicio lanza `HTTPException`: eso ataría la regla de dominio al transporte.
"""

from __future__ import annotations

from typing import Any, ClassVar
from uuid import UUID


class ErrorDominio(Exception):
    slug: ClassVar[str]
    status: ClassVar[int]
    titulo: ClassVar[str]

    def __init__(
        self,
        detalle: str | None = None,
        *,
        novel_id: UUID | str | None = None,
        generacion_id: UUID | str | None = None,
        capitulo: int | None = None,
        intentos_restantes: int | None = None,
        traza_langfuse_id: str | None = None,
        datos_faltantes: list[dict[str, Any]] | None = None,
        contradicciones: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(detalle or self.titulo)
        self.detalle = detalle
        self.extensiones: dict[str, Any] = {
            "novel_id": str(novel_id) if novel_id is not None else None,
            "generacion_id": str(generacion_id) if generacion_id is not None else None,
            "capitulo": capitulo,
            "intentos_restantes": intentos_restantes,
            "traza_langfuse_id": traza_langfuse_id,
            "datos_faltantes": datos_faltantes,
            "contradicciones": contradicciones,
        }


class PeticionInvalida(ErrorDominio):
    slug = "peticion-invalida"
    status = 422
    titulo = "La petición no cumple el schema"


class BriefInvalido(ErrorDominio):
    slug = "brief-invalido"
    status = 400
    titulo = "El brief no es válido como encargo"


class NovelaNoEncontrada(ErrorDominio):
    slug = "novela-no-encontrada"
    status = 404
    titulo = "Novela no encontrada"


class VersionNoEncontrada(ErrorDominio):
    slug = "version-no-encontrada"
    status = 404
    titulo = "Versión no encontrada"


class HechoNoEncontrado(ErrorDominio):
    slug = "hecho-no-encontrado"
    status = 404
    titulo = "Hecho no encontrado"


class GeneracionEnCurso(ErrorDominio):
    slug = "generacion-en-curso"
    status = 409
    titulo = "Ya hay una generación en curso para esta novela"


class TransicionInvalida(ErrorDominio):
    slug = "transicion-invalida"
    status = 409
    titulo = "La máquina de estados no permite esta transición"


class TrabajoNoCabeEnPool(ErrorDominio):
    slug = "trabajo-no-cabe-en-pool"
    status = 422
    titulo = "El trabajo no cabe en el presupuesto en vuelo"


class LimiteDeIntentosAgotado(ErrorDominio):
    slug = "limite-de-intentos-agotado"
    status = 409
    titulo = "Se agotaron los intentos del capítulo"


class PalabraProhibidaPersistente(ErrorDominio):
    slug = "palabra-prohibida-persistente"
    status = 409
    titulo = "Una palabra prohibida persiste tras las reescrituras permitidas"


class ExportNoDisponible(ErrorDominio):
    slug = "export-no-disponible"
    status = 404
    titulo = "El PDF de esta versión no está disponible"


class ErrorInterno(ErrorDominio):
    slug = "error-interno"
    status = 500
    titulo = "Error interno"


CATALOGO: tuple[type[ErrorDominio], ...] = (
    PeticionInvalida,
    BriefInvalido,
    NovelaNoEncontrada,
    VersionNoEncontrada,
    HechoNoEncontrado,
    GeneracionEnCurso,
    TransicionInvalida,
    TrabajoNoCabeEnPool,
    LimiteDeIntentosAgotado,
    PalabraProhibidaPersistente,
    ExportNoDisponible,
    ErrorInterno,
)
