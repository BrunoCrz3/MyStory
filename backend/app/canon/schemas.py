"""Contratos de `canon/` (RI-02).

`Consolidacion` es el contrato del unico punto que modifica el canon. Lleva el
**texto** de la escena aceptada porque RF-CANON-11 se comprueba contra el, y
`canon/` no es dueno de `Borrador`: quien consolida se lo pasa. Asi el anclaje
se verifica sin que esta feature dependa de `process/`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.canon.models import (
    Contradiccion,
    EstadoDePromesa,
    EstadoEpistemico,
    EstatusDeHecho,
    HechoCanonico,
    PromesaNarrativa,
    SnapshotDeMundo,
    TipoDeHecho,
)


class _Esquema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class NuevoHechoCanonico(_Esquema):
    texto: str
    tipo: TipoDeHecho
    estatus: EstatusDeHecho = EstatusDeHecho.PROVISIONAL
    sujeto_personaje_id: int | None = None
    objeto_personaje_id: int | None = None
    lugar_id: int | None = None
    artefacto_id: int | None = None
    valor: str | None = None
    sucede_a_hecho_id: int | None = None


class NuevaPromesaNarrativa(_Esquema):
    texto: str
    tipo: str = "setup"
    artefacto_id: int | None = None


class NuevoEstadoEpistemico(_Esquema):
    personaje_id: int
    hecho_id: int | None = None
    indice_del_hecho: int | None = None
    certeza: str | None = None


class Consolidacion(_Esquema):
    escena_id: int
    version: int
    texto: str
    fecha_ficcional: str | None = None
    hechos: list[NuevoHechoCanonico] = []
    promesas: list[NuevaPromesaNarrativa] = []
    epistemicos: list[NuevoEstadoEpistemico] = []


class ResultadoDeConsolidacion(_Esquema):
    snapshot: SnapshotDeMundo
    hechos: list[HechoCanonico]
    promesas: list[PromesaNarrativa]
    epistemicos: list[EstadoEpistemico]


class Relacion(_Esquema):
    sujeto_personaje_id: int
    objeto_personaje_id: int
    valor: str | None = None


class SnapshotDerivado(_Esquema):
    """El estado del mundo en `t`, calculado a partir de los hechos vigentes."""

    escena_id: int
    fecha_ficcional: str | None = None
    personajes_vivos: list[int] = []
    ubicaciones: dict[int, int] = {}
    posesiones: dict[int, int] = {}
    relaciones: list[Relacion] = []


class Cambio(_Esquema):
    tipo: TipoDeHecho
    sujeto_personaje_id: int | None = None
    artefacto_id: int | None = None


class SimulacionDeRetcon(_Esquema):
    """RF-CANON-09: v1 responde, no aplica."""

    hecho_id: int
    escenas_invalidadas: list[int]
    contradicciones: list[Contradiccion] = []


class LineaDeEstancamiento(_Esquema):
    id: int
    nombre: str
    escenas_sin_avanzar: int
    supera_umbral: bool | None = None


class InformeDeEstancamiento(_Esquema):
    escena_actual_id: int | None = None
    umbrales_declarados: bool
    arcos: list[LineaDeEstancamiento] = []
    hilos: list[LineaDeEstancamiento] = []
    promesas: list[LineaDeEstancamiento] = []


class TransicionDeHecho(_Esquema):
    destino: EstatusDeHecho


class TransicionDePromesa(_Esquema):
    destino: EstadoDePromesa
    escena_de_pago_id: int | None = None
