"""Las cinco transformaciones de `config/thresholds.yaml` § `guardrail.normalizacion`.

Se aplican **a los dos lados**: al texto del capítulo y a la palabra de la lista. Cada una
se puede apagar por separado, y apagarla abre exactamente el agujero de su variante
(`architecture.md` § Hooks y policy engine).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from app.commons.config.modelos import Normalizacion

# Separadores que se intercalan dentro de una palabra para esquivar el filtro: `i-d-i-o-t-a`.
# Con `quitar_signos` se eliminan; sin él, parten la palabra.
SEPARADORES_INTRA = frozenset("-_.*·'’`´~+|/\\^")
# Diminutivos y aumentativos regulares, del más largo al más corto.
SUFIJOS_VARIANTE = (
    "itos",
    "itas",
    "illos",
    "illas",
    "ito",
    "ita",
    "illo",
    "illa",
    "ote",
    "otes",
    "azo",
    "aza",
    "azos",
    "azas",
)
_LETRAS_PROPIAS = {"ñ": "ñ", "Ñ": "Ñ"}


@dataclass(frozen=True)
class Token:
    raiz: str
    inicio: int
    fin: int


def _sin_acento(c: str) -> str:
    if c in _LETRAS_PROPIAS:
        return c
    descompuesto = unicodedata.normalize("NFD", c)
    return "".join(x for x in descompuesto if not unicodedata.combining(x))


def raiz(palabra: str, reglas: Normalizacion) -> str:
    t = palabra
    if reglas.plurales:
        if len(t) > 4 and t.endswith("es"):
            t = t[:-2]
        elif len(t) > 3 and t.endswith("s"):
            t = t[:-1]
    if reglas.variantes_simples:
        for sufijo in sorted(SUFIJOS_VARIANTE, key=len, reverse=True):
            if t.endswith(sufijo) and len(t) - len(sufijo) >= 4:
                t = t[: -len(sufijo)]
                break
        if len(t) > 4 and t[-1] in "aoeAOE":
            t = t[:-1]
    return t


def tokenizar(texto: str, reglas: Normalizacion) -> list[Token]:
    """Palabras normalizadas del texto, cada una con su posición en el texto original."""
    tokens: list[Token] = []
    actual: list[str] = []
    inicio = fin = 0

    def cerrar() -> None:
        if actual:
            tokens.append(Token(raiz("".join(actual), reglas), inicio, fin))
            actual.clear()

    for i, c in enumerate(texto):
        if reglas.quitar_signos and c in SEPARADORES_INTRA:
            continue
        convertido = _sin_acento(c) if reglas.quitar_acentos else c
        if not convertido.isalnum():
            cerrar()
            continue
        if reglas.minusculas:
            convertido = convertido.lower()
        if not actual:
            inicio = i
        actual.append(convertido)
        fin = i + 1
    cerrar()
    return tokens


def raices(expresion: str, reglas: Normalizacion) -> tuple[str, ...]:
    return tuple(t.raiz for t in tokenizar(expresion, reglas))
