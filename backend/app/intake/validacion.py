"""Validación del brief parcial (RF-INTAKE-01, TO-037).

La lista de obligatorios **se deriva del propio `BriefNovela`**, no se escribe a mano: si el
modelo gana o pierde un campo obligatorio, la validación lo sigue sin que nadie la toque. Un
obligatorio que no llega, o llega vacío o en blanco, es un `Dato faltante` con su pregunta de
reintento: el sistema repregunta y **nunca rellena el hueco** (CLAUDE.md regla 4).
"""

from __future__ import annotations

import types
import typing
from typing import Any

from pydantic import BaseModel

from app.commons.config import Config
from app.intake import reglas
from app.intake.schemas import (
    BriefNovela,
    BriefNovelaParcial,
    DatoFaltante,
    ResultadoValidacionBrief,
)


def _modelo(tipo: Any) -> type[BaseModel] | None:
    """El modelo Pydantic que hay dentro de una anotación, si lo hay (quitando `| None`)."""
    if isinstance(tipo, type) and issubclass(tipo, BaseModel):
        return tipo
    if typing.get_origin(tipo) in (typing.Union, types.UnionType):
        modelos = [m for a in typing.get_args(tipo) if (m := _modelo(a)) is not None]
        return modelos[0] if len(modelos) == 1 else None
    return None


def _obligatorios(modelo: type[BaseModel], prefijo: str = "") -> list[str]:
    rutas: list[str] = []
    for nombre, campo in modelo.model_fields.items():
        tipo = campo.annotation
        if typing.get_origin(tipo) is list:
            item = _modelo(typing.get_args(tipo)[0])
            if item is not None:
                rutas += _obligatorios(item, f"{prefijo}{nombre}[].")
            continue
        sub = _modelo(tipo)
        if sub is not None and campo.is_required():
            rutas += _obligatorios(sub, f"{prefijo}{nombre}.")
        elif campo.is_required():
            rutas.append(f"{prefijo}{nombre}")
    return rutas


OBLIGATORIOS: tuple[str, ...] = tuple(_obligatorios(BriefNovela))

PREGUNTAS: dict[str, str] = {
    "comprador.identificador": "¿Con qué identificador quieres que te reconozcamos, sin "
    "correo ni nombre?",
    "destinatario.nombre": "¿Cómo se llama la persona a quien regalas la novela?",
    "destinatario.edad": "¿Cuántos años tiene?",
    "ocasion.tipo": "¿Con qué motivo se la regalas?",
    "genero": "¿Qué género te gustaría para la novela?",
    "tono": "¿Qué tono quieres que tenga?",
    "dedicatoria.texto": "¿Qué quieres que diga la dedicatoria?",
    "elementos_personalizados[].enunciado": "¿Qué detalle personal quieres que aparezca?",
    "elementos_personalizados[].obligatorio": "¿Ese detalle tiene que aparecer sí o sí?",
    "textos_libres[].contenido": "¿Qué querías contarnos en ese texto?",
}


def _vacio(valor: Any) -> bool:
    return valor is None or (isinstance(valor, str) and not valor.strip())


def _faltantes(datos: Any, partes: list[str], ruta: str) -> list[str]:
    """Las rutas concretas que faltan para una ruta de `OBLIGATORIOS`."""
    cabeza, resto = partes[0], partes[1:]
    if cabeza.endswith("[]"):
        lista = datos.get(cabeza[:-2]) if isinstance(datos, dict) else None
        if not isinstance(lista, list):
            return []  # una lista que no llega no obliga a nada: sus elementos no existen
        return [
            f
            for i, elemento in enumerate(lista)
            for f in _faltantes(elemento, resto, f"{ruta}{cabeza[:-2]}[{i}].")
        ]
    valor = datos.get(cabeza) if isinstance(datos, dict) else None
    if not resto:
        return [f"{ruta}{cabeza}"] if _vacio(valor) else []
    return _faltantes(valor, resto, f"{ruta}{cabeza}.")


def datos_faltantes(brief: BriefNovelaParcial) -> list[DatoFaltante]:
    datos = brief.model_dump(mode="json")
    return [
        DatoFaltante(campo=campo, pregunta_reintento=PREGUNTAS[obligatorio])
        for obligatorio in OBLIGATORIOS
        for campo in _faltantes(datos, obligatorio.split("."), "")
    ]


def validar(config: Config, brief: BriefNovelaParcial) -> ResultadoValidacionBrief:
    """Analiza el brief sin crear nada: faltantes y contradicciones. Los fragmentos
    sospechosos y los hechos del texto libre llegan con el P36."""
    faltantes = datos_faltantes(brief)
    contradicciones = reglas.contradicciones(config, brief)
    return ResultadoValidacionBrief(
        valido=not faltantes and not contradicciones,
        datos_faltantes=faltantes,
        contradicciones=contradicciones,
        fragmentos_sospechosos=[],
        hechos_extraidos=[],
    )
