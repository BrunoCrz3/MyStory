"""Llamada al editor: corrige el borrador a partir del informe de crítica (RF-QUA-05).

Devuelve la salida cruda para que el ciclo la pase por **todos** los validadores, empezando
por `schema_valido`: el editor no tiene un camino de validación propio.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from app.commons.llm import SalidaInvalida, SalidaTruncada
from app.commons.llm.esquema import esquema_de_salida
from app.commons.recursos import Recursos
from app.context import service as context
from app.guardrail import service as guardrail
from app.intake.service import leer_brief
from app.quality import service as quality

ESQUEMA_EDITOR = esquema_de_salida(quality.SalidaEditor)


class Correccion(BaseModel):
    """Lo que el editor devolvió: el borrador para revalidar y los defectos sistémicos."""

    model_config = ConfigDict(frozen=True)

    datos: dict[str, Any] | None
    error: str | None
    sistemicos: list[str]


async def corregir(
    r: Recursos,
    *,
    novel_id: str,
    version: int,
    numero: int,
    titulo: str,
    texto: str,
    informe: list[str],
) -> Correccion:
    def leer(con: sqlite3.Connection) -> dict[str, list[context.Pieza]]:
        brief = leer_brief(con, novel_id=novel_id)
        bc = context.brief_de_capitulo(con, novel_id=novel_id, numero=numero)
        assert brief is not None and bc is not None, "el ciclo ya leyó brief y capítulo"
        return context.piezas_editor(
            con,
            r.config,
            novel_id=novel_id,
            version=version,
            numero=numero,
            brief=brief,
            brief_capitulo=bc,
            palabras_novela=[p.forma for p in guardrail.palabras_de_novela(con, novel_id=novel_id)],
            titulo=titulo,
            texto=texto,
            informe=informe,
        )

    with r.trazador.span("consultar_story_bible", entrada={"capitulo": numero, "rol": "editor"}):
        piezas = await r.db.ejecutar(leer)
    ensamblador = context.Ensamblador(r.config, context.ContadorProveedor(r.llamador))
    ensamblado = await ensamblador.ensamblar(
        "editor",
        piezas,
        tarea=f"Corrige el capítulo {numero} según el informe y devuelve el capítulo completo.",
        esquema_salida=ESQUEMA_EDITOR,
    )
    try:
        respuesta = await r.llamador.llamar(ensamblado.peticion)
    except (SalidaInvalida, SalidaTruncada) as e:
        return Correccion(datos=None, error=str(e), sistemicos=[])
    try:
        salida = quality.SalidaEditor.model_validate(respuesta.datos)
    except ValidationError as e:
        motivo = f"la salida del editor no cumple su schema: {e.error_count()} errores"
        return Correccion(datos=None, error=motivo, sistemicos=[])
    return Correccion(
        datos={"titulo": salida.titulo, "texto": salida.texto},
        error=None,
        sistemicos=[d.defecto for d in salida.clasificacion if d.clasificacion == "sistémico"],
    )
