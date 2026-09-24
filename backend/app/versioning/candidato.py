"""Hecho candidato de una solicitud por fragmento (RF-VER-07, TO-011, D-19).

Sin embeddings (TO-015): similitud de Jaccard sobre tokens normalizados entre el fragmento
que seleccionó el lector y el `fragmento_soporte` de los hechos que **usa** el capítulo de
origen. Por debajo de `regeneracion.similitud_hecho_candidato` no se propone nada. A igual
similitud gana el hecho establecido antes: es el original, el que el lector quiere cambiar.
La propuesta nunca regenera: el lector confirma.
"""

from __future__ import annotations

import re

from app.canon.service import Hecho
from app.commons.texto import plano

_PALABRA = re.compile(r"\w+")


def _tokens(texto: str) -> set[str]:
    return set(_PALABRA.findall(plano(texto)))


def similitud(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def candidato(fragmento: str, hechos: list[Hecho], *, umbral: float) -> Hecho | None:
    puntuados = [
        (similitud(fragmento, h.fragmento_soporte or ""), h) for h in hechos if h.fragmento_soporte
    ]
    validos = [(s, h) for s, h in puntuados if s >= umbral]
    if not validos:
        return None
    return min(validos, key=lambda p: (-p[0], p[1].capitulo_establece or 0))[1]
