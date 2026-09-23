"""Capa 1 de la ontologia. Una clase por clase de `docs/definitions.md`.

Los nombres son los de la ontologia, exactos (AGENTS.md regla 1, RNF-07). Un
nombre nuevo sin entrada en `definitions.md` es un error, no una mejora, y hay
un comprobador en CI que lo dice: `tests/reglas/test_ontologia.py`.

`Parte / Acto` se llama `Parte` aqui, que es la primera forma de la ontologia.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class EstadoDeEscena(StrEnum):
    """Los cinco estados del diagrama de `domain-knowledge.md`, ni uno mas.

    La extraccion no esta: es el paso que sigue a `aceptada`, no un estado.
    """

    PLANIFICADA = "planificada"
    EN_BORRADOR = "en_borrador"
    EN_REVISION = "en_revision"
    ACEPTADA = "aceptada"
    OBSOLETA = "obsoleta"


class ModoDeAceptacion(StrEnum):
    """Como se llego a `aceptada`. RF-PROC-07, P-19.

    Lo que hay que poder distinguir no es *quien* acepto --hay un solo autor por
    instancia-- sino **como**: aceptacion humana frente a automatica. De esa
    distincion depende entera la utilidad de `training_samples`, y ademas es el
    ultimo cortafuegos de la resistencia a inyeccion: ningun agente acepta.

    El defecto es `AUTOMATICA`, y es deliberado. Un defecto permisivo dejaria
    que cualquier llamada que se olvide del argumento aceptara una escena.
    """

    HUMANA = "humana"
    AUTOMATICA = "automatica"


class EstadoDeHilo(StrEnum):
    """Situacion de un `Hilo de trama`.

    La ontologia da a `Hilo de trama` el atributo `estado` **sin enumerar sus
    valores**, igual que hace con `Hecho canonico.tipo`. Se enumera aqui con el
    mismo riesgo asumido y la misma consecuencia escrita: `canon_huerfano`
    necesita saber que hilos siguen abiertos, y sin un valor de cierre la
    medida no podria bajar nunca al cerrar uno. Un hilo sin `estado` cuenta como
    abierto: no declarar no es cerrar.
    """

    ABIERTO = "abierto"
    CERRADO = "cerrado"


# La maquina de estados, tal cual la dibuja el diagrama. Las transiciones no van
# al esquema: SQLite no las expresa y un trigger las esconderia del sitio donde
# se leen las reglas.
TRANSICIONES: dict[EstadoDeEscena, frozenset[EstadoDeEscena]] = {
    EstadoDeEscena.PLANIFICADA: frozenset({EstadoDeEscena.EN_BORRADOR}),
    EstadoDeEscena.EN_BORRADOR: frozenset({EstadoDeEscena.EN_REVISION}),
    EstadoDeEscena.EN_REVISION: frozenset(
        {EstadoDeEscena.EN_BORRADOR, EstadoDeEscena.PLANIFICADA, EstadoDeEscena.ACEPTADA}
    ),
    EstadoDeEscena.ACEPTADA: frozenset({EstadoDeEscena.OBSOLETA}),
    EstadoDeEscena.OBSOLETA: frozenset({EstadoDeEscena.PLANIFICADA}),
}


class _Entidad(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    id: int


# Alias publico para anotar genericos sin exponer el guion bajo. Es un alias, no
# una clase: el comprobador de la ontologia mira `ClassDef`, y aqui no hay una.
Entidad = _Entidad


# --- Clases estructurales -------------------------------------------------


class Obra(_Entidad):
    titulo: str | None = None
    premisa: str
    genero: str
    extension_objetivo: int | None = None
    publico: str | None = None


class Parte(_Entidad):
    obra_id: int
    orden: int
    funcion_dramatica: str
    punto_de_giro: str | None = None


class Capitulo(_Entidad):
    parte_id: int
    orden: int
    pov_dominante_id: int | None = None
    gancho_de_cierre: str | None = None


class Escena(_Entidad):
    capitulo_id: int
    orden: int
    estado: EstadoDeEscena
    objetivo: str | None = None
    conflicto: str | None = None
    resultado: str | None = None
    personaje_pov_id: int | None = None
    lugar_id: int | None = None
    momento: str | None = None
    estado_de_entrada: str | None = None
    estado_de_salida: str | None = None


class Beat(_Entidad):
    escena_id: int
    orden: int
    valor_inicial: str | None = None
    valor_final: str | None = None


# --- Entidades narrativas -------------------------------------------------


class Personaje(_Entidad):
    nombre: str
    deseo: str | None = None
    necesidad: str | None = None
    herida: str | None = None
    rol_narrativo: str | None = None
    arco_id: int | None = None


class Voz(_Entidad):
    personaje_id: int
    lexico: str | None = None
    registro: str | None = None
    sintaxis: str | None = None
    muletillas: str | None = None
    temas_recurrentes: str | None = None


class Arco(_Entidad):
    nombre: str
    estado_inicial: str | None = None
    puntos_de_giro: str | None = None
    estado_final: str | None = None


class HiloDeTrama(_Entidad):
    nombre: str
    tipo: str
    pregunta_dramatica: str | None = None
    estado: str | None = None


class Lugar(_Entidad):
    nombre: str
    geografia: str | None = None
    atmosfera_sensorial: str | None = None
    reglas_propias: str | None = None


class Faccion(_Entidad):
    nombre: str
    objetivo: str | None = None
    recursos: str | None = None


class Artefacto(_Entidad):
    nombre: str
    propiedades: str | None = None
    poseedor_actual_id: int | None = None
    deuda_narrativa: str | None = None


class Novum(_Entidad):
    nombre: str
    mecanismo: str
    limites: str
    consecuencias_en_cascada: str | None = None


class ReglaDelMundo(_Entidad):
    novum_id: int
    enunciado: str
    alcance: str | None = None
    excepciones_declaradas: str | None = None


class TerminoCanonico(_Entidad):
    forma: str
    definicion: str | None = None
    novum_id: int | None = None
    primera_aparicion_id: int | None = None
    variantes_prohibidas: str | None = None


class Tema(_Entidad):
    nombre: str
    enunciado: str | None = None


class Motivo(_Entidad):
    nombre: str
    forma: str | None = None
    evolucion: str | None = None


class VozNarrativa(_Entidad):
    obra_id: int
    persona: str | None = None
    tiempo_verbal: str | None = None
    distancia: str | None = None
    focalizacion: str | None = None
    ratio_escena_resumen: str | None = None


class Evento(_Entidad):
    """Suceso de la fabula. Se narra en cero, una o varias escenas."""

    que_ocurre: str
    momento_en_la_fabula: str | None = None
    duracion: str | None = None


class Objetivo(_Entidad):
    personaje_id: int
    enunciado: str
    alcance: str | None = None
    tipo: str | None = None
    estado: str | None = None
