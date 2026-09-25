"""**Hook de policy** del alcance («dos hooks: uno de validación del capítulo y otro de
policy»): conformidad de schema y guardrail de palabras prohibidas, lo barato y determinista
que corre antes que nada, en el span `hook_policy` (`architecture.md` § Hooks y policy engine).

El otro, el **hook de validación del capítulo**, es `quality.service.hook_capitulo`: siete
validadores programáticos en paralelo, en el span `hook_capitulo`, que solo corre si este pasa.

Lo ejecuta `process/` porque es quien puede usar `guardrail/`; la decisión sobre el capítulo
la toma después el policy engine con los veredictos (TO-039, A-31).
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.commons.config import Config
from app.guardrail.service import Coincidencia, Guardrail, PerfilLector
from app.process.schemas import BorradorCapitulo
from app.quality.service import Defecto, ResultadoValidador


def schema_valido(
    datos: dict[str, Any] | None, error: str | None
) -> tuple[ResultadoValidador, BorradorCapitulo | None]:
    borrador: BorradorCapitulo | None = None
    motivo = error
    if motivo is None:
        try:
            borrador = BorradorCapitulo.model_validate(datos)
        except ValidationError as e:
            motivo = f"la salida no es un borrador de capítulo: {e.error_count()} errores"
    if borrador is not None and (not borrador.titulo.strip() or not borrador.texto.strip()):
        motivo, borrador = "el título o el texto del capítulo están vacíos", None
    pasa = borrador is not None
    resultado = ResultadoValidador(
        nombre="schema_valido",
        tipo="programático",
        punto="hook de policy",
        pasa=pasa,
        valor=1.0 if pasa else 0.0,
        cierra_el_paso=True,
        detalle="la salida cumple su schema" if pasa else str(motivo),
        defectos=[]
        if pasa
        else [Defecto(dimension="schema_valido", gravedad="alta", descripcion=str(motivo))],
    )
    return resultado, borrador


def palabras_prohibidas(
    config: Config, borrador: BorradorCapitulo, *, palabras_novela: list[str], perfil: PerfilLector
) -> tuple[ResultadoValidador, list[Coincidencia]]:
    texto = f"{borrador.titulo}\n\n{borrador.texto}"
    coincidencias = Guardrail(config).comprobar(
        texto, palabras_novela=palabras_novela, perfil=perfil
    )
    pasa = not coincidencias
    detalle = (
        "ninguna palabra prohibida"
        if pasa
        else "; ".join(f"«{c.fragmento}» (nivel {c.nivel})" for c in coincidencias)
    )
    return (
        ResultadoValidador(
            nombre="palabras_prohibidas",
            tipo="programático",
            punto="hook de policy",
            pasa=pasa,
            valor=1.0 if pasa else 0.0,
            cierra_el_paso=True,
            detalle=detalle,
            defectos=[
                Defecto(
                    dimension="palabras_prohibidas",
                    gravedad="alta",
                    descripcion=f"quita «{c.fragmento}» en cualquiera de sus formas",
                    localizacion=f"carácter {c.inicio}",
                )
                for c in coincidencias
            ],
        ),
        coincidencias,
    )
