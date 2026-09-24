"""Editor: la salida estructurada de la corrección y el informe que la guía (RF-QUA-05).

El editor recibe el borrador y los defectos que cierran el paso —de los hooks y del judge—,
y devuelve el capítulo corregido y la clasificación de cada defecto. Su salida vuelve a
pasar **todos** los validadores. Un defecto que clasifica como sistémico se trata como local
en la demo y queda en el audit log con su clasificación (D-14).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.quality.models import ResultadoValidador

_GRAVEDAD = {"alta": 0, "media": 1, "baja": 2}


class DefectoClasificado(BaseModel):
    model_config = ConfigDict(extra="forbid")

    defecto: str
    clasificacion: Literal["local", "sistémico"]


class SalidaEditor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str
    texto: str
    clasificacion: list[DefectoClasificado]


def defectos_que_cierran(resultados: list[ResultadoValidador]) -> bool:
    return any(not v.pasa and v.cierra_el_paso for v in resultados)


def informe_para_editor(resultados: list[ResultadoValidador]) -> list[str]:
    """Los defectos que el editor tiene que corregir, de más a menos graves.

    Van los de todo validador que falla y cierra el paso; los que solo puntúan se quedan en
    el informe de crítica, pero no justifican una llamada al modelo.
    """
    defectos = [
        (d.gravedad, f"[{v.nombre}] {d.descripcion}")
        for v in resultados
        if not v.pasa and v.cierra_el_paso
        for d in (v.defectos or [])
    ]
    defectos += [
        ("media", f"[{v.nombre}] {v.detalle}")
        for v in resultados
        if not v.pasa and v.cierra_el_paso and not v.defectos
    ]
    return [texto for _, texto in sorted(defectos, key=lambda d: _GRAVEDAD[d[0]])]
