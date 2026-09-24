"""Análisis de impacto de un cambio sobre un hecho (RF-VER-09).

Se calcula sobre la relación **usa**, no sobre **establece**: un hecho establecido en el 2 y
mencionado en el 7 obliga a reescribir los dos (`architecture.md` § Regeneración dirigida).
El capítulo que lo estableció se añade siempre, porque también es quien lo cuenta. Los
hechos que establecen los capítulos afectados son **derivados**: al reescribirse, pueden
cambiar.
"""

from __future__ import annotations

from uuid import UUID

from app.canon.service import Hecho
from app.versioning.schemas import AnalisisImpacto


def analizar(hecho: Hecho, vigentes: list[Hecho]) -> AnalisisImpacto:
    afectados = set(hecho.capitulos_usan)
    if hecho.capitulo_establece is not None:
        afectados.add(hecho.capitulo_establece)
    derivados = [
        UUID(h.hecho_id)
        for h in vigentes
        if h.hecho_id != hecho.hecho_id and h.capitulo_establece in afectados
    ]
    return AnalisisImpacto(capitulos_afectados=sorted(afectados), hechos_derivados=derivados)
