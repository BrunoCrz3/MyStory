"""Salidas del extractor de prueba, ancladas en el texto que se les da."""

from __future__ import annotations

from typing import Any


def extraccion(
    texto: str,
    *,
    fragmentos: list[str] | None = None,
    usados: list[str] | None = None,
    elementos: list[str] | None = None,
    promesas: list[str] | None = None,
    pagadas: list[str] | None = None,
    reabiertas: list[str] | None = None,
) -> dict[str, Any]:
    """Una extracción cuyos hechos citan fragmentos literales de `texto`."""
    if fragmentos is None:
        primera = texto.split(".")[0]
        fragmentos = [primera]
    return {
        "hechos_nuevos": [
            {"enunciado": f"Se cuenta que: {f}", "tipo": "suceso", "fragmento_soporte": f}
            for f in fragmentos
        ],
        "hechos_usados": usados or [],
        "eventos": [
            {
                "descripcion": "Marta mira el horizonte",
                "orden": 1,
                "lugar": "el puerto",
                "personajes": ["Marta"],
            },
        ],
        "promesas_abiertas": [{"enunciado": p, "tipo": "pregunta"} for p in (promesas or [])],
        "promesas_pagadas": pagadas or [],
        "promesas_reabiertas": reabiertas or [],
        "elementos_presentes": elementos or [],
        "personajes_presentes": ["Marta"],
        "ubicaciones": [{"personaje": "Marta", "lugar": "el puerto"}],
        "resumen": "Marta mira el mar y decide volver.",
        "gancho_cierre": "El barco la espera.",
    }
