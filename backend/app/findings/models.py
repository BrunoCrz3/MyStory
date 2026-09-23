"""Modo hibrido: lo que la escritura descubre y el plan no habia previsto.

Las tres clases que `architecture.md` seccion Anatomia de una feature asigna a
`findings/` y que son clases: `Hallazgo`, `Estado de hallazgo` y `Extraccion`.
La cuarta entrada de esa fila, «adopcion», no es una clase sino la operacion, y
vive en `service.py`.

`Estado de hallazgo` es un enumerado aqui y un `CHECK` en el esquema, igual que
`Estatus de hecho` en la Capa 2: es la misma cosa dicha en dos idiomas.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class EstadoDeHallazgo(StrEnum):
    """Los cinco del ciclo de vida de `domain-knowledge.md`, ni uno mas.

    El primero se llama `propuesto`, nunca `provisional`: `provisional` es un
    estatus de `Hecho canonico` y confundirlos borraria la frontera entre «el
    sistema cree esto» y «la novela dice esto».
    """

    PROPUESTO = "propuesto"
    ADOPTADO = "adoptado"
    DESCARTADO = "descartado"
    CONFLICTIVO = "conflictivo"
    INTEGRADO = "integrado"


# El ciclo de vida, tal cual lo dibuja `domain-knowledge.md`. No va al esquema:
# SQLite cierra la lista de valores con un `CHECK` pero no sabe de que estado se
# viene, y un trigger lo escondería del sitio donde se leen las reglas.
#
# `Conflictivo` es el punto de decision del metodo: ahi se elige entre defender
# el plan o dejar que la novela cambie de rumbo. `Integrado` y `Descartado` son
# terminales.
TRANSICIONES_DEL_HALLAZGO: dict[EstadoDeHallazgo, frozenset[EstadoDeHallazgo]] = {
    EstadoDeHallazgo.PROPUESTO: frozenset({EstadoDeHallazgo.ADOPTADO, EstadoDeHallazgo.DESCARTADO}),
    EstadoDeHallazgo.ADOPTADO: frozenset(
        {EstadoDeHallazgo.INTEGRADO, EstadoDeHallazgo.CONFLICTIVO}
    ),
    EstadoDeHallazgo.CONFLICTIVO: frozenset(
        {EstadoDeHallazgo.INTEGRADO, EstadoDeHallazgo.DESCARTADO}
    ),
    EstadoDeHallazgo.INTEGRADO: frozenset(),
    EstadoDeHallazgo.DESCARTADO: frozenset(),
}

# Estados en los que el hallazgo ya es verdad de la novela. Hasta llegar aqui es
# memoria larga, no canon: la diferencia es exactamente lo que P-21 protege.
ESTADOS_ADOPTADOS = frozenset({EstadoDeHallazgo.ADOPTADO, EstadoDeHallazgo.INTEGRADO})


class TipoDeHallazgo(StrEnum):
    """Los cuatro de `definitions.md`. No se anade ninguno."""

    HECHO = "hecho"
    PROMESA = "promesa"
    MOTIVO = "motivo"
    PERSONAJE = "personaje"


class ModoDeAdopcion(StrEnum):
    """Como se decidio sobre un hallazgo.

    Es hermana de `ModoDeAceptacion` y esta separada a proposito: son dos
    decisiones distintas del autor --aceptar una escena y adoptar un hallazgo--
    y cada una tiene su propia puerta. Un solo enumerado con dos puertas se
    verifica peor que dos enumerados con una cada uno.

    El defecto es `AUTOMATICA` por el mismo motivo que alli: un defecto
    permisivo dejaria que cualquier llamada que se olvide del argumento adoptara
    un hallazgo, y adoptar un hallazgo equivale a cambiar la novela.
    """

    HUMANA = "humana"
    AUTOMATICA = "automatica"


class FuenteDelHallazgo(StrEnum):
    """De donde salio la propuesta.

    No es ontologia: es trazabilidad, y sirve para lo que P-25 pide poder
    distinguir. Una propuesta que sale de un detector determinista se audita de
    otra manera que una que sale de un modelo leyendo la escena.
    """

    ENTIDAD_NO_CANONICA = "entidad_no_canonica"
    MOTIVO_NO_DECLARADO = "motivo_no_declarado"
    CANDIDATURA = "candidatura"


class _Entidad(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    id: int


Entidad = _Entidad


class Extraccion(_Entidad):
    """Lectura automatica de una escena aceptada para detectar hallazgos.

    `registro_id` es `None` en la extraccion determinista de v1, que no llama al
    modelo. Lo lleva la candidatura que si venga de uno.
    """

    escena_id: int
    version: int
    entradas: str
    confianza: float | None = None
    registro_id: int | None = None
    extraido_en: str


class Hallazgo(_Entidad):
    extraccion_id: int
    escena_id: int
    tipo: TipoDeHallazgo
    estado: EstadoDeHallazgo
    texto: str
    fuente: FuenteDelHallazgo
    confianza: float | None = None
    hecho_id: int | None = None
    promesa_id: int | None = None
    motivo_id: int | None = None
    personaje_id: int | None = None
    decidido_por: str | None = None
    decidido_en: str | None = None
    propuesto_en: str
