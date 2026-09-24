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


def guion_completo(modelo: ModeloGuionizado, brief: dict[str, Any] | None = None) -> None:
    """Planificador, redactor y extractor responden siempre con una salida válida.

    El extractor declara presentes en cada capítulo todos los elementos del brief, para que
    la novela pase `elementos_obligatorios` en el gate.
    """
    brief = brief or brief_ejemplo()
    elementos = [e["enunciado"] for e in brief["elementos_personalizados"]]
    modelo.por_defecto.update(
        {
            "planificador": lambda p: esquema_valido(brief),
            "redactor": redactar,
            "extractor": partial(extraer, elementos=elementos),
        }
    )
