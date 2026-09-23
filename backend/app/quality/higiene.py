"""Puerta de higiene: determinista, sin modelo y **antes** de la critica.

Es la solucion picara #15, y lo que la hace valiosa no es el ahorro sino el
sitio: corre antes del punto unico de promocion, asi que «Aqui tienes la escena»
no llega al canon ni a `training_samples`. Las ocho comprobaciones fallan en
milisegundos y ninguna necesita modelo.

El punto ciego esta declarado y se asume: no cubre el metatexto escrito como
prosa narrativa.
"""

from __future__ import annotations

import re
import unicodedata
from enum import StrEnum


class Fallo(StrEnum):
    METATEXTO = "metatexto"
    RECHAZO = "rechazo"
    TRUNCAMIENTO = "truncamiento"
    PLACEHOLDER = "placeholder"
    IDIOMA = "idioma"
    FORMATO = "formato"
    LONGITUD = "longitud"


# El modelo hablando de su propio trabajo, no de la novela.
METATEXTO = (
    r"aqui tienes",
    r"aqui esta la escena",
    r"espero que (te guste|sirva)",
    r"he supuesto",
    r"^\s*\[?nota\b",
    r"\[nota:",
    r"como me pediste",
    r"claro,? (aqui|te)",
)

RECHAZO = (
    r"lo siento,? no puedo",
    r"no puedo (continuar|ayudar|generar|escribir)",
    r"como modelo de lenguaje",
    r"no me es posible",
    r"va en contra de mis",
)

# Marcadores de plantilla sin rellenar.
PLACEHOLDER = (
    r"\[[A-Z_]{4,}\]",
    r"\{\{[^}]*\}\}",
    r"\bTODO\b",
    r"\bXXX\b",
    r"<insertar[^>]*>",
    r"\blorem ipsum\b",
)

# Marcado de markdown en lo que deberia ser prosa.
FORMATO = (
    r"^#{1,6}\s",
    r"\*\*[^*]+\*\*",
    r"^\s*[-*+]\s+\S",
    r"^\s*\d+\.\s+\S",
    r"```",
)

CIERRES_DE_FRASE = ".!?…\"»')"

# Deteccion de idioma por palabras vacias. No necesita dependencia ni modelo, y
# distingue lo unico que hay que distinguir aqui: si la escena salio en el
# idioma de la obra o en el del entrenamiento.
VACIAS_ES = frozenset(
    [
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "de",
        "del",
        "al",
        "y",
        "o",
        "pero",
        "que",
        "se",
        "su",
        "sus",
        "con",
        "por",
        "para",
        "no",
        "ni",
        "como",
        "mas",
        "cuando",
        "donde",
        "porque",
        "sin",
        "sobre",
        "entre",
        "hasta",
        "desde",
        "muy",
        "ya",
    ]
)
VACIAS_EN = frozenset(
    [
        "the",
        "a",
        "an",
        "of",
        "and",
        "or",
        "but",
        "that",
        "with",
        "by",
        "for",
        "from",
        "into",
        "over",
        "under",
        "not",
        "no",
        "as",
        "if",
        "then",
        "than",
        "when",
        "where",
        "because",
        "about",
        "between",
        "until",
        "since",
        "very",
        "already",
        "did",
        "was",
    ]
)
PROPORCION_MINIMA_DEL_IDIOMA = 0.6
PALABRAS_MINIMAS_PARA_DECIDIR_IDIOMA = 12


def _sin_tildes(texto: str) -> str:
    return "".join(
        letra
        for letra in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(letra) != "Mn"
    )


def _alguno(patrones: tuple[str, ...], texto: str) -> bool:
    return any(re.search(patron, texto, re.IGNORECASE | re.MULTILINE) for patron in patrones)


def metatexto(texto: str) -> bool:
    return _alguno(METATEXTO, _sin_tildes(texto))


def rechazo(texto: str) -> bool:
    return _alguno(RECHAZO, _sin_tildes(texto))


def truncamiento(texto: str) -> bool:
    """La ultima frase termina. Un borrador cortado a mitad no es una escena."""
    limpio = texto.strip()
    return bool(limpio) and limpio[-1] not in CIERRES_DE_FRASE


def placeholder(texto: str) -> bool:
    return _alguno(PLACEHOLDER, texto)


def formato_roto(texto: str) -> bool:
    return _alguno(FORMATO, texto)


def idioma_ajeno(texto: str) -> bool:
    """Mezcla de idiomas. Con poco texto no decide: se abstiene."""
    palabras = re.findall(r"[a-zñáéíóúü]+", texto.lower())
    if len(palabras) < PALABRAS_MINIMAS_PARA_DECIDIR_IDIOMA:
        return False
    espanolas = sum(1 for palabra in palabras if palabra in VACIAS_ES)
    inglesas = sum(1 for palabra in palabras if palabra in VACIAS_EN)
    if espanolas + inglesas == 0:
        return False
    return espanolas / (espanolas + inglesas) < PROPORCION_MINIMA_DEL_IDIOMA


def longitud_fuera_de_objetivo(
    texto: str, objetivo_de_la_obra: int | None, escenas: int, desviacion: float | None
) -> bool | None:
    """La unica comprobacion con margen, y la unica que puede no decidir.

    `higiene.desviacion_longitud_escena` es `[decision]` y sigue en `null`. Sin
    margen declarado no se puede decir si una escena es demasiado larga, y
    inventar el numero seria ponerle una cifra al gusto del autor. Devuelve
    `None`: no evaluable.
    """
    if desviacion is None or not objetivo_de_la_obra or escenas <= 0:
        return None
    esperada = objetivo_de_la_obra / escenas
    medida = len(texto.split())
    return abs(medida - esperada) / esperada > desviacion
