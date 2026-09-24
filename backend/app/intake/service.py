"""Servicio del encargo: lo único de `intake/` que otra feature puede importar.

`intake/` es una hoja del grafo de importación: solo depende de `commons/` (D-08).
"""

from __future__ import annotations

import sqlite3

from app.commons.config import Config
from app.commons.errores import BriefInvalido
from app.intake import repository, validacion
from app.intake.schemas import (
    BriefNovela,
    BriefNovelaParcial,
    Comprador,
    Dedicatoria,
    Destinatario,
    ElementoPersonalizado,
    Ocasion,
    ResultadoValidacionBrief,
    TextoLibre,
    VozNarrativa,
)

__all__ = [
    "BriefNovela",
    "Comprador",
    "Dedicatoria",
    "Destinatario",
    "ElementoPersonalizado",
    "Ocasion",
    "TextoLibre",
    "VozNarrativa",
    "elementos_personalizados",
    "exigir_brief_valido",
    "leer_brief",
    "registrar_brief",
    "validar_brief",
]


def registrar_brief(
    con: sqlite3.Connection, *, novel_id: str, brief: BriefNovela, ahora: str
) -> None:
    """Persiste el brief validado. Va dentro de la transacción de quien crea la novela."""
    repository.insertar_brief(con, novel_id=novel_id, brief=brief, ahora=ahora)


def leer_brief(con: sqlite3.Connection, *, novel_id: str) -> BriefNovela | None:
    return repository.leer_brief(con, novel_id=novel_id)


def elementos_personalizados(
    con: sqlite3.Connection, *, novel_id: str
) -> list[tuple[str, str, bool]]:
    """`(id, enunciado, obligatorio)` de cada elemento personalizado del brief."""
    return repository.leer_elementos(con, novel_id=novel_id)


def validar_brief(config: Config, brief: BriefNovelaParcial) -> ResultadoValidacionBrief:
    """Analiza un brief parcial sin crear nada (RF-INTAKE-01)."""
    return validacion.validar(config, brief)


def exigir_brief_valido(config: Config, brief: BriefNovela) -> None:
    """Un `BriefNovela` que cumple el schema pero no vale como encargo —un campo en blanco,
    dos campos que se contradicen— es `brief-invalido`, antes de escribir nada."""
    resultado = validacion.validar(config, BriefNovelaParcial.model_validate(brief.model_dump()))
    if resultado.valido:
        return
    raise BriefInvalido(
        f"Hay {len(resultado.datos_faltantes)} datos vacíos y "
        f"{len(resultado.contradicciones)} contradicciones sin resolver.",
        datos_faltantes=[d.model_dump(exclude_none=True) for d in resultado.datos_faltantes],
        contradicciones=[c.model_dump(exclude_none=True) for c in resultado.contradicciones],
    )
