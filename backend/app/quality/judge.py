"""Judge: la salida estructurada de la rúbrica y su evaluación (RF-QUA-04, RF-QUA-07).

Seis criterios, cada uno con su puntuación 0–1 y su justificación, y cada uno emite el score
del validador semántico que sostiene (`docs/verification.md` § Índice). La llamada al modelo
la hace `process/`, que es quien ensambla el contexto; aquí vive el contrato de la salida y
qué significa cada puntuación: si pasa su umbral de `calidad` y si cierra el paso, que
mientras `medicion.cerrar_el_paso` sea `false` no ocurre nunca.

`arco` es la mitad semántica de `cierre_arco` (D-15): el judge la puntúa en cada capítulo y
el gate usa la del último.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.commons.config import Config
from app.quality.models import Defecto, ResultadoValidador
from app.quality.registro import validador

# Criterio de la rúbrica (clave de la salida del judge) → score del registro.
CRITERIO_A_SCORE: dict[str, str] = {
    "continuidad": "consistencia_factica",
    "tono": "adecuacion_tono",
    "arco": "cierre_arco",
    "coherencia_personajes": "coherencia_personajes",
    "ritmo": "ritmo",
    "personalizacion_natural": "personalizacion_natural",
}


class Puntuacion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    puntuacion: float = Field(ge=0, le=1)
    justificacion: str = Field(min_length=1)


class AfirmacionDestinatario(BaseModel):
    """Un hecho personal que el capítulo afirma sobre el destinatario (D-13, P37)."""

    model_config = ConfigDict(extra="forbid")

    afirmacion: str
    fragmento: str


class TemaExcluidoVisto(BaseModel):
    """Si un tema excluido aparece en el capítulo, aunque no se nombre (D-13, P37)."""

    model_config = ConfigDict(extra="forbid")

    tema: str
    aparece: bool
    fragmento: str


class SalidaJudge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    continuidad: Puntuacion
    tono: Puntuacion
    arco: Puntuacion
    coherencia_personajes: Puntuacion
    ritmo: Puntuacion
    personalizacion_natural: Puntuacion
    afirmaciones_destinatario: list[AfirmacionDestinatario]
    temas_excluidos: list[TemaExcluidoVisto]


class ResultadoJudge(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_valido: ResultadoValidador
    criterios: list[ResultadoValidador]
    salida: SalidaJudge | None

    @property
    def todos(self) -> list[ResultadoValidador]:
        return [self.schema_valido, *self.criterios]


def _schema(motivo: str | None) -> ResultadoValidador:
    v = validador("schema_valido")
    pasa = motivo is None
    return ResultadoValidador(
        nombre=v.nombre,
        tipo=v.tipo,
        punto=v.punto,
        pasa=pasa,
        valor=1.0 if pasa else 0.0,
        cierra_el_paso=True,
        detalle="la salida del judge cumple su schema" if pasa else f"judge: {motivo}",
        defectos=[]
        if pasa
        else [Defecto(dimension="schema_valido", gravedad="alta", descripcion=f"judge: {motivo}")],
    )


def _criterio(config: Config, nombre: str, p: Puntuacion) -> ResultadoValidador:
    v = validador(nombre)
    umbral: float | None = getattr(config.umbrales.calidad, nombre)
    # Sin umbral no hay con qué suspender: el score queda y el paso no se decide por él.
    pasa = umbral is None or p.puntuacion >= umbral
    return ResultadoValidador(
        nombre=nombre,
        tipo=v.tipo,
        punto=v.punto,
        pasa=pasa,
        valor=p.puntuacion,
        cierra_el_paso=config.umbrales.medicion.cerrar_el_paso,
        detalle=p.justificacion,
        defectos=[]
        if pasa
        else [Defecto(dimension=nombre, gravedad="media", descripcion=p.justificacion)],
    )


def evaluar_judge(
    config: Config, datos: dict[str, Any] | None, error: str | None
) -> ResultadoJudge:
    """La salida del judge como resultados de validador: `schema_valido` y seis criterios."""
    if error is not None:
        return ResultadoJudge(schema_valido=_schema(error), criterios=[], salida=None)
    try:
        salida = SalidaJudge.model_validate(datos)
    except ValidationError as e:
        motivo = f"la salida no cumple la rúbrica: {e.error_count()} errores"
        return ResultadoJudge(schema_valido=_schema(motivo), criterios=[], salida=None)
    criterios = [
        _criterio(config, nombre, getattr(salida, criterio))
        for criterio, nombre in CRITERIO_A_SCORE.items()
    ]
    return ResultadoJudge(schema_valido=_schema(None), criterios=criterios, salida=salida)
