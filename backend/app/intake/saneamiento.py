"""Saneamiento del texto libre: los `Fragmento sospechoso` salen antes de llegar a un modelo
(RF-INTAKE-03, RNF-09, D-20).

El texto se parte en líneas y frases; la que casa con un patrón de `patrones.txt` se devuelve
como sospechosa y se retira del texto limpio, que es lo único que sigue adelante. Es una lista
determinista y versionada: auditable, y sin modelo que se pueda engañar para que no la vea.
"""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.intake.schemas import FragmentoSospechoso

_PATRONES = Path(__file__).with_name("patrones.txt")
# Fin de frase: signo final seguido de espacio. Un punto dentro de una palabra —`.env`,
# `permissions.allow`— no parte la frase, o dejaría medio fragmento en el texto limpio.
_FIN_DE_FRASE = re.compile(r"(?<=[.!?…])\s+")


class Saneado(BaseModel):
    model_config = ConfigDict(frozen=True)

    limpio: str
    fragmentos: list[FragmentoSospechoso]


@cache
def patrones() -> tuple[tuple[re.Pattern[str], str], ...]:
    lineas = _PATRONES.read_text(encoding="utf-8").splitlines()
    resultado = []
    for linea in lineas:
        if not linea.strip() or linea.startswith("#"):
            continue
        expresion, motivo = linea.split("\t", 1)
        resultado.append((re.compile(expresion, re.IGNORECASE | re.MULTILINE), motivo.strip()))
    return tuple(resultado)


def _motivo(frase: str) -> str | None:
    return next((motivo for patron, motivo in patrones() if patron.search(frase)), None)


def sanear(texto: str) -> Saneado:
    lineas_limpias: list[str] = []
    fragmentos: list[FragmentoSospechoso] = []
    for linea in texto.splitlines():
        conservadas: list[str] = []
        for trozo in _FIN_DE_FRASE.split(linea):
            frase = trozo.strip()
            if not frase:
                continue
            motivo = _motivo(frase)
            if motivo is None:
                conservadas.append(frase)
            else:
                fragmentos.append(FragmentoSospechoso(fragmento=frase, motivo=motivo))
        if conservadas:
            lineas_limpias.append(" ".join(conservadas))
    return Saneado(limpio="\n".join(lineas_limpias), fragmentos=fragmentos)
