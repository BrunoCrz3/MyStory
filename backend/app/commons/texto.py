"""Utilidades de texto sin dominio: recuento de palabras y normalización para comparar."""

from __future__ import annotations

import re
import unicodedata

_PALABRA = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*|\d+", re.UNICODE)


def palabras(texto: str) -> list[str]:
    return _PALABRA.findall(texto)


def contar_palabras(texto: str) -> int:
    """Palabras de un texto: secuencias de letras, con guion o apóstrofo interno, o números."""
    return len(palabras(texto))


def plano(texto: str) -> str:
    """Minúsculas y sin acentos, conservando la ñ: la forma con que se comparan nombres."""
    resultado = []
    for c in texto.lower():
        if c == "ñ":
            resultado.append(c)
            continue
        descompuesto = unicodedata.normalize("NFD", c)
        resultado.append("".join(x for x in descompuesto if not unicodedata.combining(x)))
    return "".join(resultado)
