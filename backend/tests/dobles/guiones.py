"""Guiones completos para el doble del modelo: una novela entera sin llamar al proveedor."""

from __future__ import annotations

import re
from functools import partial
from typing import Any

from app.commons.llm import Peticion
from tests.dobles.modelo import ModeloGuionizado
from tests.fixtures.borradores import borrador
from tests.fixtures.briefs import brief_ejemplo
from tests.fixtures.esquemas import esquema_valido
from tests.fixtures.extracciones import extraccion
from tests.fixtures.judge import salida_judge


def numero_de_la_tarea(peticion: Peticion) -> int:
    m = re.search(r"Escribe el capítulo (\d+)", peticion.mensajes[0].contenido)
    return int(m.group(1)) if m else 0


def capitulo_aceptado_de(peticion: Peticion) -> str:
    local = peticion.mensajes[0].contenido.split('<capa nombre="local">', 1)[1]
    local = local.split("</capa>", 1)[0]
    return next(ln for ln in local.splitlines() if ln.strip() and not ln.endswith(":"))


def redactar(peticion: Peticion) -> dict[str, str]:
    n = numero_de_la_tarea(peticion)
    return borrador(titulo=f"Capítulo {n}: la travesía")


def extraer(peticion: Peticion, elementos: list[str] | None = None) -> dict[str, Any]:
    return extraccion(capitulo_aceptado_de(peticion), elementos=elementos)


def corregido(palabras: int = 1200, **kw: str) -> dict[str, Any]:
    """Salida del editor: un borrador y la clasificación de los defectos que corrige."""
    return {**borrador(palabras, **kw), "clasificacion": []}


def guion_revision(modelo: ModeloGuionizado) -> None:
    """Judge, editor y entrevistador por defecto: el judge aprueba los seis criterios, el
    editor devuelve un borrador válido y el entrevistador no extrae ningún hecho. Una prueba
    que necesite otra cosa la encola antes."""
    modelo.por_defecto.setdefault("judge", lambda p: salida_judge())
    modelo.por_defecto.setdefault("editor", lambda p: corregido())
    modelo.por_defecto.setdefault("entrevistador", lambda p: {"hechos": []})


def guion_completo(modelo: ModeloGuionizado, brief: dict[str, Any] | None = None) -> None:
    """Planificador, redactor y extractor responden siempre con una salida válida.

    El extractor declara presentes en cada capítulo todos los elementos del brief, para que
    la novela pase `elementos_obligatorios` en el gate.
    """
    guion_revision(modelo)
    brief = brief or brief_ejemplo()
    elementos = [e["enunciado"] for e in brief["elementos_personalizados"]]
    modelo.por_defecto.update(
        {
            "planificador": lambda p: esquema_valido(brief),
            "redactor": redactar,
            "extractor": partial(extraer, elementos=elementos),
        }
    )
