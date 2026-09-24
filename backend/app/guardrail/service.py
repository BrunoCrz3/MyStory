"""`Guardrail`: el veto de palabras prohibidas sobre un texto (RF-GUARD-01, RF-GUARD-02).

Los tres niveles se aplican en conjunto y gana el más restrictivo. El registro de cada
`Coincidencia` en el audit log y en Langfuse lo hace quien decide sobre el capítulo
(`policy/`), porque el guardrail no conoce el capítulo ni la traza.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from app.commons.config import Config
from app.commons.config.modelos import Normalizacion
from app.guardrail import repository
from app.guardrail.models import RESTRICCION, Coincidencia, PalabraProhibida
from app.guardrail.normalizacion import raices, tokenizar

LISTAS = Path(__file__).resolve().parent / "listas"

__all__ = [
    "Coincidencia",
    "Guardrail",
    "PalabraProhibida",
    "PerfilLector",
    "palabras_de_novela",
    "registrar_palabras_novela",
]


@dataclass(frozen=True)
class PerfilLector:
    """Lo que el nivel `perfil` necesita saber del destinatario y de la ocasión."""

    edad: int
    ocasion: str


@cache
def _lista_global() -> tuple[str, ...]:
    lineas = (LISTAS / "global.txt").read_text(encoding="utf-8").splitlines()
    return tuple(ln.strip() for ln in lineas if ln.strip() and not ln.lstrip().startswith("#"))


class _ListasPerfil(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    adolescente: list[str]
    infantil: list[str]
    ocasiones: dict[str, list[str]]


@cache
def _listas_perfil() -> _ListasPerfil:
    crudo = yaml.safe_load((LISTAS / "perfil.yaml").read_text(encoding="utf-8"))
    return _ListasPerfil.model_validate(crudo)


class Guardrail:
    def __init__(self, config: Config, normalizacion: Normalizacion | None = None) -> None:
        self.config = config
        self.reglas = normalizacion or config.umbrales.guardrail.normalizacion

    def palabras_perfil(self, perfil: PerfilLector) -> list[str]:
        cortes = self.config.umbrales.guardrail.perfil
        listas = _listas_perfil()
        palabras: list[str] = []
        if perfil.edad <= cortes.edad_maxima_adolescente:
            palabras += listas.adolescente
        if perfil.edad <= cortes.edad_maxima_infantil:
            palabras += listas.infantil
        palabras += listas.ocasiones.get(perfil.ocasion, [])
        return palabras

    def palabras(
        self, *, palabras_novela: list[str], perfil: PerfilLector
    ) -> list[PalabraProhibida]:
        """Las tres listas en conjunto: `global`, `perfil` y `novela`."""
        niveles = self.config.umbrales.guardrail.niveles
        resultado: list[PalabraProhibida] = []
        if "global" in niveles:
            resultado += [
                PalabraProhibida(forma=p, nivel="global", origen="lista global")
                for p in _lista_global()
            ]
        if "perfil" in niveles:
            resultado += [
                PalabraProhibida(
                    forma=p, nivel="perfil", origen=f"perfil edad {perfil.edad}, {perfil.ocasion}"
                )
                for p in self.palabras_perfil(perfil)
            ]
        if "novela" in niveles:
            resultado += [
                PalabraProhibida(forma=p, nivel="novela", origen="brief") for p in palabras_novela
            ]
        return resultado

    def comprobar(
        self, texto: str, *, palabras_novela: list[str], perfil: PerfilLector
    ) -> list[Coincidencia]:
        tokens = tokenizar(texto, self.reglas)
        raices_texto = [t.raiz for t in tokens]
        mejores: dict[tuple[int, int], tuple[PalabraProhibida, int, int]] = {}
        for palabra in self.palabras(palabras_novela=palabras_novela, perfil=perfil):
            patron = raices(palabra.forma, self.reglas)
            if not patron:
                continue
            n = len(patron)
            for i in range(len(raices_texto) - n + 1):
                if tuple(raices_texto[i : i + n]) != patron:
                    continue
                inicio, fin = tokens[i].inicio, tokens[i + n - 1].fin
                previa = mejores.get((inicio, fin))
                if previa is None or RESTRICCION[palabra.nivel] > RESTRICCION[previa[0].nivel]:
                    mejores[(inicio, fin)] = (palabra, inicio, fin)
        return [
            Coincidencia(
                palabra=p.forma,
                nivel=p.nivel,
                inicio=inicio,
                fin=fin,
                fragmento=texto[inicio:fin],
            )
            for (p, inicio, fin) in sorted(mejores.values(), key=lambda x: (x[1], x[2]))
        ]


def registrar_palabras_novela(
    con: sqlite3.Connection, *, novel_id: str, palabras: list[str]
) -> None:
    """Guarda el nivel `novela` que declara el comprador (RF-INTAKE-05)."""
    repository.insertar_palabras(con, novel_id=novel_id, palabras=palabras, origen="brief")


def palabras_de_novela(con: sqlite3.Connection, *, novel_id: str) -> list[PalabraProhibida]:
    return repository.leer_palabras(con, novel_id=novel_id)
