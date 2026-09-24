"""Esquemas de obra de prueba, coherentes con un brief ficticio."""

from __future__ import annotations

import copy
from typing import Any

LUGARES = ["el puerto", "el faro", "la casa de la playa"]


def esquema_valido(brief: dict[str, Any], capitulos: int = 10) -> dict[str, Any]:
    destinataria = brief["destinatario"]["nombre"]
    obligatorios = [
        e["enunciado"] for e in brief.get("elementos_personalizados", []) if e["obligatorio"]
    ]
    plan = []
    for n in range(1, capitulos + 1):
        plan.append(
            {
                "numero": n,
                "titulo_provisional": f"Capítulo {n}: la travesía",
                "funcion_dramatica": "planteamiento" if n == 1 else "desarrollo",
                "pov": destinataria,
                "lugar": LUGARES[n % len(LUGARES)],
                "estado_entrada": f"Estado al empezar el capítulo {n}.",
                "restriccion": {
                    "tipo": "estado_final",
                    "enunciado": f"Al cerrar el {n}, {destinataria} está más cerca del mar.",
                    "alcance": [
                        {"tipo": "personaje", "nombre": destinataria},
                        {"tipo": "lugar", "nombre": LUGARES[n % len(LUGARES)]},
                    ],
                },
                "elementos": obligatorios if n == 2 else [],
            }
        )
    return {
        "titulo": "El verano del Alondra",
        "premisa": "Una travesía que es también un regreso.",
        "personajes": [
            {
                "nombre": destinataria,
                "deseo": "volver al mar",
                "herida": "un verano perdido",
                "rol_narrativo": "protagonista",
                "voz": "directa y tozuda",
                "es_destinatario": True,
            },
            {
                "nombre": "Tomás",
                "deseo": "que ella no se vaya",
                "herida": "miedo al agua",
                "rol_narrativo": "aliado",
                "voz": "pausada",
                "es_destinatario": False,
            },
        ],
        "lugares": [
            {"nombre": lugar, "geografia": "costa", "atmosfera": "salitre"} for lugar in LUGARES
        ],
        "hilos": [{"nombre": "El regreso", "pregunta_dramatica": "¿Volverá a navegar?"}],
        "capitulos": plan,
    }


def con_cambios(esquema: dict[str, Any], **cambios: Any) -> dict[str, Any]:
    nuevo = copy.deepcopy(esquema)
    nuevo.update(cambios)
    return nuevo
