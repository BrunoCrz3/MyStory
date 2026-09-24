"""Extracción de hechos del texto libre por el `interviewer`: la tool
`extraer_hechos_texto_libre` (RF-INTAKE-03, TO-017).

Recibe el texto **ya saneado**: los `Fragmento sospechoso` no llegan al modelo. El texto va
en el mensaje de usuario dentro de `<texto_libre_no_confiable>`, con los ángulos escapados
para que nada de él pueda cerrar la etiqueta; el system es el prompt del rol, fijo y sin
datos de la novela (A-18, A-25).

Un hecho solo se propone si su fragmento está **literalmente** en el texto limpio: lo que el
modelo deduzca, complete o saque de una instrucción que se le escapó al saneamiento no pasa.
Los hechos vuelven con `origen: texto-libre` y como propuestos: adoptarlos es del policy
engine, nunca del texto.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, ValidationError

from app.commons.llm import Mensaje, Peticion, SalidaInvalida, SalidaTruncada
from app.commons.llm.esquema import esquema_de_salida
from app.commons.recursos import Recursos
from app.intake.schemas import HechoTextoLibre
from app.prompts import prompt_de, skills_de

ETIQUETA = "texto_libre_no_confiable"


class HechoPropuesto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enunciado: str
    fragmento: str


class SalidaEntrevistador(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hechos: list[HechoPropuesto]


ESQUEMA_ENTREVISTADOR = esquema_de_salida(SalidaEntrevistador)


def _escapar(texto: str) -> str:
    return texto.replace("<", "‹").replace(">", "›")


def _normal(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip().lower()


def peticion_extraccion(textos: list[str]) -> Peticion:
    prompt = prompt_de("entrevistador")
    system = "\n\n".join([prompt.texto, *(s.texto for s in skills_de("entrevistador"))])
    datos = "\n\n".join(f"<{ETIQUETA}>\n{_escapar(t)}\n</{ETIQUETA}>" for t in textos)
    return Peticion(
        rol="entrevistador",
        system=system,
        mensajes=[
            Mensaje(
                role="user",
                contenido=f"{datos}\n\n<tarea>\nExtrae los hechos que el texto afirma, cada "
                "uno con su fragmento literal.\n</tarea>",
            )
        ],
        esquema_salida=ESQUEMA_ENTREVISTADOR,
        prompt=prompt.nombre,
        hash_prompt=prompt.hash_git,
    )


async def extraer_hechos(r: Recursos, textos: list[str]) -> list[HechoTextoLibre]:
    textos = [t for t in textos if t.strip()]
    if not textos:
        return []
    with r.trazador.span("extraer_hechos_texto_libre", entrada={"textos": len(textos)}):
        try:
            respuesta = await r.llamador.llamar(peticion_extraccion(textos))
            salida = SalidaEntrevistador.model_validate(respuesta.datos)
        except (SalidaInvalida, SalidaTruncada, ValidationError) as e:
            # La validación responde igual: sin hechos, y el fallo queda en la traza.
            r.trazador.score("schema_valido", 0.0, comentario=f"entrevistador: {e}"[:2000])
            return []
    limpio = _normal(" ".join(textos))
    return [
        HechoTextoLibre(enunciado=h.enunciado, origen="texto-libre")
        for h in salida.hechos
        if h.fragmento.strip() and _normal(h.fragmento) in limpio
    ]
