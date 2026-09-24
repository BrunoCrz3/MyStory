"""Cuerpo de error RFC 9457 y su forma en el OpenAPI.

`DatoFaltanteProblema` y `ContradiccionProblema` son la **forma de transporte** de dos
clases de `intake/` dentro de un error: `commons/` no conoce la ontología y no importa
`intake/`, así que el error lleva su propia copia de la forma (TO-038, A-04).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.commons.esquemas import opcional

TipoProblema = Literal[
    "/problemas/peticion-invalida",
    "/problemas/brief-invalido",
    "/problemas/novela-no-encontrada",
    "/problemas/version-no-encontrada",
    "/problemas/hecho-no-encontrado",
    "/problemas/generacion-en-curso",
    "/problemas/transicion-invalida",
    "/problemas/trabajo-no-cabe-en-pool",
    "/problemas/limite-de-intentos-agotado",
    "/problemas/palabra-prohibida-persistente",
    "/problemas/export-no-disponible",
    "/problemas/error-interno",
]


class DatoFaltanteProblema(BaseModel):
    campo: str
    pregunta_reintento: str | None = opcional()


class ContradiccionProblema(BaseModel):
    campos: list[str]
    tipo: Literal["edad-vs-tono", "edad-vs-genero", "fecha-vs-edad", "otra"]
    explicacion: str | None = opcional()


class Problema(BaseModel):
    type: TipoProblema
    title: str
    status: Annotated[int, Field(ge=400, le=599)]
    detail: str | None = opcional()
    instance: str | None = opcional(format="uri-reference")
    novel_id: UUID | None = None
    generacion_id: UUID | None = None
    capitulo: Annotated[int, Field(ge=1)] | None = None
    intentos_restantes: Annotated[int, Field(ge=0)] | None = None
    traza_langfuse_id: str | None = None
    datos_faltantes: list[DatoFaltanteProblema] = Field(default_factory=list)
    contradicciones: list[ContradiccionProblema] = Field(default_factory=list)

    def cuerpo(self) -> dict[str, Any]:
        datos = self.model_dump(mode="json", exclude_none=True)
        for lista in ("datos_faltantes", "contradicciones"):
            if not datos.get(lista):
                datos.pop(lista, None)
        return datos
