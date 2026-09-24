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


_UNIDADES = (
    "cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
    "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete",
    "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés",
    "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho",
    "veintinueve",
)  # fmt: skip
_DECENAS = {3: "treinta", 4: "cuarenta", 5: "cincuenta", 6: "sesenta", 7: "setenta",
            8: "ochenta", 9: "noventa"}  # fmt: skip


def numero_en_letras(n: int) -> str:
    """Un número de 0 a 120 escrito en letra, como lo escribiría una novela."""
    if n < 0 or n > 120:
        return str(n)
    if n < 30:
        return _UNIDADES[n]
    if n < 100:
        decena, unidad = divmod(n, 10)
        return _DECENAS[decena] + ("" if unidad == 0 else f" y {_UNIDADES[unidad]}")
    return "cien" if n == 100 else f"ciento {numero_en_letras(n - 100)}"
