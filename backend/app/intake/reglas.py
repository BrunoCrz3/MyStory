"""Reglas deterministas entre campos del brief (RF-INTAKE-02, RNF-16).

Cada regla mira solo los campos que compara y se aplica en cuanto llegan los dos, aunque
falten otros: el formulario avisa de una contradicción sin esperar a que el brief esté
completo. Las listas de marcadores son deliberadamente cortas y auditables; lo que no
capturan lo cubre el judge con `adecuacion_tono` sobre el texto ya escrito.
"""

from __future__ import annotations

import re
from datetime import date

from app.commons.config import Config
from app.commons.texto import plano
from app.intake.schemas import BriefNovelaParcial, ContradiccionBrief

# Palabras de un tono o un género que no encajan con un destinatario menor de edad.
MARCADORES_TONO = frozenset(
    {
        "adulto", "adultos", "ironico", "cinico", "sarcastico", "erotico", "sensual",
        "oscuro", "violento", "crudo", "picante", "explicito", "sordido",
    }
)  # fmt: skip
MARCADORES_GENERO = frozenset(
    {
        "terror", "gore", "erotica", "erotico", "noir", "thriller", "adulto", "adultos",
        "explicito", "violento", "sangriento",
    }
)  # fmt: skip
_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PALABRA = re.compile(r"\w+")


def _marcas(texto: str, marcadores: frozenset[str]) -> list[str]:
    return sorted(set(_PALABRA.findall(plano(texto))) & marcadores)


def _edad_en(nacimiento: date, referencia: date) -> int:
    cumplidos = (referencia.month, referencia.day) >= (nacimiento.month, nacimiento.day)
    return referencia.year - nacimiento.year - (0 if cumplidos else 1)


def contradicciones(config: Config, brief: BriefNovelaParcial) -> list[ContradiccionBrief]:
    menor = config.umbrales.guardrail.perfil.edad_maxima_adolescente
    d = brief.destinatario
    edad = d.edad if d is not None else None
    resultado: list[ContradiccionBrief] = []

    if edad is not None and edad <= menor:
        for campo, texto, marcadores, tipo in (
            ("tono", brief.tono, MARCADORES_TONO, "edad-vs-tono"),
            ("genero", brief.genero, MARCADORES_GENERO, "edad-vs-genero"),
        ):
            marcas = _marcas(texto or "", marcadores)
            if marcas:
                resultado.append(
                    ContradiccionBrief(
                        campos=["destinatario.edad", campo],
                        tipo=tipo,
                        explicacion=f"«{texto}» ({', '.join(marcas)}) no encaja con una "
                        f"edad de {edad} años.",
                    )
                )
    if edad is not None and d is not None and d.fecha_nacimiento is not None:
        referencia = (brief.ocasion.fecha if brief.ocasion else None) or date.today()
        calculada = _edad_en(d.fecha_nacimiento, referencia)
        if abs(calculada - edad) > 1:
            resultado.append(
                ContradiccionBrief(
                    campos=["destinatario.fecha_nacimiento", "destinatario.edad"],
                    tipo="fecha-vs-edad",
                    explicacion=f"Nacido el {d.fecha_nacimiento}, el {referencia} tendría "
                    f"{calculada} años, no {edad}.",
                )
            )
    comprador = brief.comprador
    identificador = (comprador.identificador or "").strip() if comprador is not None else ""
    if _CORREO.match(identificador):
        resultado.append(
            ContradiccionBrief(
                campos=["comprador.identificador"],
                tipo="otra",
                explicacion="El identificador del comprador tiene forma de correo: tiene que "
                "ser una cadena opaca, nunca un dato personal (RNF-16).",
            )
        )
    return resultado
