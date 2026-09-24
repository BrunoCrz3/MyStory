"""Servicio del encargo: lo único de `intake/` que otra feature puede importar.

`intake/` es una hoja del grafo de importación: solo depende de `commons/` (D-08).
"""

from __future__ import annotations

import sqlite3

from app.commons.config import Config
from app.commons.errores import BriefInvalido
from app.commons.recursos import Recursos
from app.intake import extraccion, repository, validacion
from app.intake.saneamiento import Saneado, sanear
from app.intake.schemas import (
    BriefNovela,
    BriefNovelaParcial,
    Comprador,
    Dedicatoria,
    Destinatario,
    ElementoPersonalizado,
    FragmentoSospechoso,
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
    "sanear_brief",
    "validar_brief",
]


def sanear_brief(brief: BriefNovela) -> tuple[BriefNovela, list[FragmentoSospechoso]]:
    """El brief sin los `Fragmento sospechoso` de su texto libre, y los fragmentos retirados.
    Un texto libre que se queda vacío desaparece: no hay nada que tratar como dato."""
    saneados: list[tuple[TextoLibre, Saneado]] = [
        (t, sanear(t.contenido)) for t in brief.textos_libres
    ]
    textos = [t.model_copy(update={"contenido": s.limpio}) for t, s in saneados if s.limpio.strip()]
    fragmentos = [f for _, s in saneados for f in s.fragmentos]
    return brief.model_copy(update={"textos_libres": textos}), fragmentos


def registrar_brief(
    con: sqlite3.Connection, *, novel_id: str, brief: BriefNovela, ahora: str
) -> None:
    """Persiste el brief validado **ya saneado** y registra lo que se retiró (RF-INTAKE-03).
    Va dentro de la transacción de quien crea la novela: ningún modelo lee nunca el texto
    libre sin sanear, porque no queda guardado en ninguna parte."""
    limpio, fragmentos = sanear_brief(brief)
    repository.insertar_brief(con, novel_id=novel_id, brief=limpio, ahora=ahora)
    repository.insertar_fragmentos(con, novel_id=novel_id, fragmentos=fragmentos, ahora=ahora)


def leer_brief(con: sqlite3.Connection, *, novel_id: str) -> BriefNovela | None:
    return repository.leer_brief(con, novel_id=novel_id)


def elementos_personalizados(
    con: sqlite3.Connection, *, novel_id: str
) -> list[tuple[str, str, bool]]:
    """`(id, enunciado, obligatorio)` de cada elemento personalizado del brief."""
    return repository.leer_elementos(con, novel_id=novel_id)


async def validar_brief(r: Recursos, brief: BriefNovelaParcial) -> ResultadoValidacionBrief:
    """Analiza un brief parcial sin crear nada (RF-INTAKE-01, RF-INTAKE-03): faltantes,
    contradicciones, fragmentos sospechosos del texto libre y los hechos que el
    `interviewer` lee del texto ya saneado."""
    resultado = validacion.validar(r.config, brief)
    saneados = [sanear(t.contenido) for t in brief.textos_libres or [] if t.contenido]
    hechos = await extraccion.extraer_hechos(r, [s.limpio for s in saneados])
    return resultado.model_copy(
        update={
            "fragmentos_sospechosos": [f for s in saneados for f in s.fragmentos],
            "hechos_extraidos": hechos,
        }
    )


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
