"""Generador del fichero Lean de una versión (RF-LEAN-01, spec 4 § 3.3).

Dos piezas: `leer_cronologia` saca de la story bible lo que Lean necesita de una versión, y
`generar` lo convierte en un módulo `Cronologia.Hechos` más un índice que dice qué evento
comprueba cada teorema.

- **Determinista** (A-90): los identificadores sintéticos salen del orden de narración y del
  orden de los UUID, nunca del orden en que llegaron las filas.
- **Sin Mathlib** (A-91): solo importa `Cronologia.Basico`.
- **Sin texto libre** (regla 11): ni descripciones ni nombres; un comentario de cabecera
  enlaza cada identificador sintético con su UUID.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.novel import service as novel
from app.novel.service import EventoVigente

Invariante = Literal["ubicacion", "cronologia", "edad", "nacimiento"]
INVARIANTES: tuple[Invariante, ...] = ("ubicacion", "cronologia", "edad", "nacimiento")

# El score de cada invariante, con el nombre de `quality/registro.py` y `verification.md`.
SCORE: dict[Invariante, str] = {
    "ubicacion": "lean_ubicacion",
    "cronologia": "lean_cronologia",
    "edad": "lean_edad",
    "nacimiento": "lean_nacimiento",
}

_PREDICADO: dict[Invariante, str] = {
    "ubicacion": "ubicacionOk eventos",
    "cronologia": "cronologiaOk eventos excluyentes",
    "edad": "edadOk nacimientos",
    "nacimiento": "nacimientoOk nacimientos",
}

_ANIO = re.compile(r"^(\d{4})-\d{2}-\d{2}$")


class ExcluyenteDeVersion(BaseModel):
    model_config = ConfigDict(frozen=True)

    evento_id: str
    personaje_id: str
    tipo: str


class PersonajeDeVersion(BaseModel):
    """Un personaje con su año de nacimiento, si lo tiene. El nombre sirve para el informe al
    editor y nunca entra en el fichero."""

    model_config = ConfigDict(frozen=True)

    personaje_id: str
    nombre: str
    anio_nacimiento: int | None


class Cronologia(BaseModel):
    """Lo que Lean lee de una versión: sus eventos vigentes, excluyentes y nacimientos."""

    model_config = ConfigDict(frozen=True)

    novel_id: str
    version: int
    eventos: list[EventoVigente]
    excluyentes: list[ExcluyenteDeVersion]
    personajes: list[PersonajeDeVersion]


class Teorema(BaseModel):
    """Qué comprueba un teorema del fichero: el índice que traduce un error de Lean."""

    model_config = ConfigDict(frozen=True)

    invariante: Invariante
    evento_id: str
    numero: int
    momento: int
    personajes: list[str]


class FicheroLean(BaseModel):
    model_config = ConfigDict(frozen=True)

    texto: str
    indice: dict[int, Teorema]


def _anio_de(fecha: str | None) -> int | None:
    if fecha is None:
        return None
    m = _ANIO.match(fecha)
    return int(m.group(1)) if m else None


def leer_cronologia(
    con: sqlite3.Connection, *, novel_id: str, version: int, hasta_numero: int | None = None
) -> Cronologia:
    """La cronología vigente en `version`; con `hasta_numero`, solo la de los capítulos hasta
    ese número (el chequeo incremental, TO-016)."""
    eventos = [
        e
        for e in novel.eventos_de_version(con, novel_id=novel_id, version=version)
        if hasta_numero is None or e.numero <= hasta_numero
    ]
    ids = {e.evento_id for e in eventos}
    return Cronologia(
        novel_id=novel_id,
        version=version,
        eventos=eventos,
        excluyentes=[
            ExcluyenteDeVersion(evento_id=ev, personaje_id=p, tipo=t)
            for ev, p, t in novel.excluyentes_de_version(con, novel_id=novel_id, version=version)
            if ev in ids
        ],
        personajes=[
            PersonajeDeVersion(
                personaje_id=pid, nombre=p.nombre, anio_nacimiento=_anio_de(p.fecha_nacimiento)
            )
            for pid, p in novel.personajes_por_id(con, novel_id=novel_id).items()
        ],
    )


def _opcion(valor: int | None) -> str:
    return "none" if valor is None else f"(some {valor})"


def generar(c: Cronologia) -> FicheroLean:
    """El módulo `Cronologia.Hechos` de la cronología y su índice línea → teorema."""
    eventos = sorted(c.eventos, key=lambda e: (e.momento, e.evento_id))
    num_evento = {e.evento_id: i for i, e in enumerate(eventos, 1)}
    personajes = sorted(
        {p.personaje_id for p in c.personajes}
        | {pr.personaje_id for e in eventos for pr in e.presentes}
    )
    num_personaje = {p: i for i, p in enumerate(personajes, 1)}
    lugares = sorted({e.lugar_id for e in eventos if e.lugar_id is not None})
    num_lugar = {lugar: i for i, lugar in enumerate(lugares, 1)}

    lineas = [
        "/-",
        f"Generado desde la story bible: novela {c.novel_id}, versión {c.version}. No editar.",
        "Identificadores sintéticos (spec 4 § 3.3):",
        *(
            f"  e{num_evento[e.evento_id]} = evento {e.evento_id} (capítulo {e.numero})"
            for e in eventos
        ),
        *(f"  p{num_personaje[p]} = personaje {p}" for p in personajes),
        *(f"  l{num_lugar[lugar]} = lugar {lugar}" for lugar in lugares),
        "-/",
        "import Cronologia.Basico",
        "",
        "namespace Cronologia.Hechos",
        "open Cronologia",
        "",
    ]
    for e in eventos:
        presentes = ", ".join(
            f"Presencia.mk {num_personaje[pr.personaje_id]} {_opcion(pr.edad)}"
            for pr in sorted(e.presentes, key=lambda pr: num_personaje[pr.personaje_id])
        )
        lugar = _opcion(num_lugar[e.lugar_id] if e.lugar_id is not None else None)
        lineas.append(
            f"def e{num_evento[e.evento_id]} : Evento := Evento.mk {num_evento[e.evento_id]}"
            f" {e.momento} {_opcion(e.anio)} {lugar} [{presentes}]"
        )
    excluyentes = sorted(
        {
            (num_evento[x.evento_id], num_personaje[x.personaje_id])
            for x in c.excluyentes
            if x.evento_id in num_evento
        }
    )
    nacimientos = sorted(
        (num_personaje[p.personaje_id], p.anio_nacimiento)
        for p in c.personajes
        if p.anio_nacimiento is not None
    )
    lineas += [
        "",
        "def eventos : List Evento := ["
        + ", ".join(f"e{num_evento[e.evento_id]}" for e in eventos)
        + "]",
        "def excluyentes : List Excluyente := ["
        + ", ".join(f"Excluyente.mk {ev} {p}" for ev, p in excluyentes)
        + "]",
        "def nacimientos : List Nacimiento := ["
        + ", ".join(f"Nacimiento.mk {p} {a}" for p, a in nacimientos)
        + "]",
        "",
    ]
    indice: dict[int, Teorema] = {}
    for invariante in INVARIANTES:
        for e in eventos:
            n = num_evento[e.evento_id]
            lineas.append(
                f"theorem {invariante}_e{n} : {_PREDICADO[invariante]} e{n} = true := by decide"
            )
            indice[len(lineas)] = Teorema(
                invariante=invariante,
                evento_id=e.evento_id,
                numero=e.numero,
                momento=e.momento,
                personajes=sorted(pr.personaje_id for pr in e.presentes),
            )
    lineas += ["", "end Cronologia.Hechos", ""]
    return FicheroLean(texto="\n".join(lineas), indice=indice)
