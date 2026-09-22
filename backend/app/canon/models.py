"""Capa 2 de la ontologia: el canon y el estado del mundo.

Los nombres son los de `docs/definitions.md`, exactos, y lo comprueba
`tests/reglas/test_ontologia.py`. `Estatus de hecho` y `Estado de promesa` son
clases de la ontologia aunque en el esquema sean un `CHECK`: aqui son
enumerados, que es lo mismo dicho en Python.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class EstatusDeHecho(StrEnum):
    """Grado de fijacion de un hecho. Cinco valores: con `implicito`, sin
    `descartado` (spec §7)."""

    PROVISIONAL = "provisional"
    IMPLICITO = "implicito"
    CONFIRMADO = "confirmado"
    RETCONEADO = "retconeado"
    REFUTADO = "refutado"


class EstadoDePromesa(StrEnum):
    PENDIENTE = "pendiente"
    PAGADA = "pagada"
    SUBVERTIDA = "subvertida"
    ROTA = "rota"


class TipoDeHecho(StrEnum):
    """La mitad enumerable de `Hecho canonico.tipo`.

    El plan declara como riesgo asumido que el atributo no esta enumerado en la
    ontologia. Se implementan los cuatro tipos de los que se deriva el snapshot
    —RF-CANON-03 pide personajes vivos, ubicaciones, posesiones y relaciones— y
    todo lo demas entra como `descriptivo`, sin desglosar. La consecuencia esta
    escrita: RF-QUA-01 se queda sin la mitad descriptiva, y los ojos que cambian
    de color no los ve nadie.
    """

    ESTADO_VITAL = "estado_vital"
    UBICACION = "ubicacion"
    POSESION = "posesion"
    RELACION = "relacion"
    DESCRIPTIVO = "descriptivo"


# Tipos cuyo hecho describe un estado que otro hecho posterior puede cerrar. Un
# hecho `descriptivo` no cierra a nadie: no se sabe de que habla.
TIPOS_DE_ESTADO = frozenset(
    {
        TipoDeHecho.ESTADO_VITAL,
        TipoDeHecho.UBICACION,
        TipoDeHecho.POSESION,
        TipoDeHecho.RELACION,
    }
)

# docs/domain-knowledge.md § Ciclo de vida de un hecho canonico.
# `Refutado` es sumidero por diseno (RF-CANON-10): no se revive, se sucede.
TRANSICIONES_DEL_HECHO: dict[EstatusDeHecho, frozenset[EstatusDeHecho]] = {
    EstatusDeHecho.PROVISIONAL: frozenset({EstatusDeHecho.CONFIRMADO, EstatusDeHecho.IMPLICITO}),
    EstatusDeHecho.IMPLICITO: frozenset({EstatusDeHecho.CONFIRMADO}),
    EstatusDeHecho.CONFIRMADO: frozenset({EstatusDeHecho.RETCONEADO, EstatusDeHecho.REFUTADO}),
    EstatusDeHecho.RETCONEADO: frozenset({EstatusDeHecho.CONFIRMADO}),
    EstatusDeHecho.REFUTADO: frozenset(),
}

# docs/domain-knowledge.md § Ciclo de vida de una promesa narrativa.
# Los tres finales son terminales; `Rota` lo es por diseno declarado.
TRANSICIONES_DE_LA_PROMESA: dict[EstadoDePromesa, frozenset[EstadoDePromesa]] = {
    EstadoDePromesa.PENDIENTE: frozenset(
        {EstadoDePromesa.PAGADA, EstadoDePromesa.SUBVERTIDA, EstadoDePromesa.ROTA}
    ),
    EstadoDePromesa.PAGADA: frozenset(),
    EstadoDePromesa.SUBVERTIDA: frozenset(),
    EstadoDePromesa.ROTA: frozenset(),
}


class _Entidad(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    id: int


Entidad = _Entidad


class HechoCanonico(_Entidad):
    texto: str
    tipo: TipoDeHecho
    escena_id: int
    estatus: EstatusDeHecho
    sujeto_personaje_id: int | None = None
    objeto_personaje_id: int | None = None
    lugar_id: int | None = None
    artefacto_id: int | None = None
    valor: str | None = None
    vigente_hasta_escena_id: int | None = None
    cerrado_por_hecho_id: int | None = None
    sucede_a_hecho_id: int | None = None


class SnapshotDeMundo(_Entidad):
    """La fila. El estado del mundo no esta aqui: se deriva (RF-CANON-03)."""

    escena_id: int
    version: int
    fecha_ficcional: str | None = None


class EstadoEpistemico(_Entidad):
    personaje_id: int
    hecho_id: int
    escena_id: int
    certeza: str | None = None


class IroniaDramatica(_Entidad):
    hecho_id: int
    lo_sabe_id: int | None = None
    no_lo_sabe_id: int | None = None


class PromesaNarrativa(_Entidad):
    texto: str
    tipo: str
    estado: EstadoDePromesa
    artefacto_id: int | None = None


class Revelacion(_Entidad):
    hecho_id: int
    destinatario: str
    personaje_id: int | None = None
    escena_minima_id: int | None = None


class Contradiccion(_Entidad):
    hecho_a_id: int
    hecho_b_id: int
    tipo: str
    gravedad: str
    resolucion: str | None = None
    retcon_id: int | None = None


class Retcon(_Entidad):
    hecho_antiguo_id: int
    hecho_nuevo_id: int | None = None
    decidido_en: str | None = None
