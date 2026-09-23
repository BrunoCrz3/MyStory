"""Capa 5 de la ontologia: el ciclo de produccion.

Las siete clases que `architecture.md` seccion Anatomia de una feature asigna a
`process/`: `Esquema`, `Brief de escena`, `Restriccion de destino`, `Borrador`,
`Version`, `Registro de generacion` y `Deriva`. Los nombres son los de
`docs/definitions.md`, exactos, y lo comprueba `tests/reglas/test_ontologia.py`.

`Muestra de entrenamiento` **no esta aqui**: la tabla `training_samples` entra en
v1 por RF-PROC-09 y la ontologia todavia no la ratifica como clase (spec seccion
9, fila A-46). Darle un `models.py` seria darle un estatuto que no tiene; su
contrato vive en `schemas.py`, que es donde viven los contratos y no las clases.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class TipoDeRestriccion(StrEnum):
    """Los tres `tipo` que `definitions.md` da a `Restriccion de destino`.

    Son exactamente los tres comprobables contra un snapshot sin modelo de por
    medio, que es lo que hace ejecutable la restriccion (verification.md,
    Soluciones picaras 5).
    """

    ESTADO_FINAL = "estado_final"
    REVELACION = "revelacion"
    POSICION_DE_PERSONAJE = "posicion_de_personaje"


class OrigenDeVersion(StrEnum):
    """Quien dejo el texto de esta version.

    `autor` es el unico que no viene de una llamada al modelo, y por eso es el
    unico que puede no tener borrador detras.
    """

    REDACTOR = "redactor"
    EDITOR = "editor"
    AUTOR = "autor"


class ComponenteDeDeriva(StrEnum):
    """Los tres del vector de `definitions.md`, Medida de la deriva.

    Sin agregado escalar: comparar un vector contra un solo numero seria perder
    justo la informacion por la que es un vector.
    """

    INVALIDACION = "invalidacion"
    CANON_HUERFANO = "canon_huerfano"
    INVIABILIDAD_PAGO = "inviabilidad_pago"


class TipoDeElemento(StrEnum):
    """Que clase de cosa entro en una cuenta de la deriva.

    `HALLAZGO` esta declarado y en v1 no lo produce nadie: `findings/` llega en
    H7. Cuando llegue, los hallazgos adoptados desde el ultimo hito de plan
    entran en `canon_huerfano` sin tocar ni el esquema ni esta enumeracion.
    """

    RESTRICCION_DESTINO = "restriccion_destino"
    HILO_DE_TRAMA = "hilo_de_trama"
    PROMESA_NARRATIVA = "promesa_narrativa"
    HALLAZGO = "hallazgo"


class CuentaEn(StrEnum):
    """Con que papel entro un elemento en la medicion."""

    NUMERADOR = "numerador"
    DENOMINADOR = "denominador"
    # Solo `inviabilidad_pago`: las restricciones futuras que podrian pagar una
    # promesa. Como no se sabe cual paga cual, el numerador se deduce contando.
    CANDIDATO = "candidato"


class MotivoDeIngrediente(StrEnum):
    """Por que un elemento cuenta. Texto corto y enumerado, no prosa libre.

    Es lo que permite recalcular el historico con una definicion distinta: un
    motivo en prosa habria que volver a leerlo a mano.
    """

    # Invalidacion
    RESTRICCION_FUTURA_VIGENTE = "restriccion_futura_vigente"
    ESTADO_FINAL_IMPOSIBLE = "estado_final_imposible"
    POSICION_IMPOSIBLE = "posicion_imposible"
    REVELACION_YA_OCURRIDA = "revelacion_ya_ocurrida"
    HECHO_REFUTADO = "hecho_refutado"
    # Canon huerfano
    CANON_ABIERTO = "canon_abierto"
    ABIERTO_DESPUES_DEL_HITO = "abierto_despues_del_hito"
    # Inviabilidad de pago
    PROMESA_PENDIENTE = "promesa_pendiente"
    CANDIDATA_DE_PAGO = "candidata_de_pago"


class _Entidad(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    id: int


Entidad = _Entidad


class Esquema(_Entidad):
    """Un hito de plan: la huella del plan vigente y por que se movio.

    `Esquema` es la estructura planificada de partes, capitulos y escenas, y esa
    estructura ya vive en `novel/`. Lo que `process/` necesita de ella es el
    unico dato que el ciclo usa: **cuando dejo de ser la misma**. El `plan_hash`
    es la huella del conjunto de restricciones de destino aun no escritas, y el
    motivo es la etiqueta con la que se calibra la deriva (RF-PROC-13).
    """

    plan_hash: str
    motivo: str
    # Posicion del discurso al fijarse el hito: la de la ultima escena aceptada
    # entonces. Es lo que ancla «desde el ultimo hito de plan» sin relojes.
    posicion: int
    fijado_en: str


class BriefDeEscena(_Entidad):
    """Minimo por diseno: estado de entrada mas restriccion de destino.

    No se planifican beats. La escena descubre *como*, no *hacia donde*.
    """

    escena_id: int
    estado_de_entrada: str
    encargo: str | None = None
    creado_en: str


class RestriccionDeDestino(_Entidad):
    brief_id: int
    tipo: TipoDeRestriccion
    enunciado: str
    alcance: str | None = None
    personaje_id: int | None = None
    lugar_id: int | None = None
    hecho_id: int | None = None
    valor: str | None = None


class RegistroDeGeneracion(_Entidad):
    escena_id: int | None = None
    agente: str
    modelo: str
    prompt: str
    contexto: str
    semilla: str | None = None
    huella_prompt: str
    huella_contexto: str
    huella_parametros: str
    tokens_de_entrada: int | None = None
    tokens_de_salida: int | None = None
    timeout_segundos: float
    registrado_en: str


class Borrador(_Entidad):
    brief_id: int
    escena_id: int
    intento: int
    texto: str
    registro_id: int
    creado_en: str


class Version(_Entidad):
    escena_id: int
    numero: int
    borrador_id: int | None = None
    texto: str
    origen: OrigenDeVersion
    creada_en: str


class Deriva(_Entidad):
    """La medicion de una escena aceptada.

    Numerador y denominador por separado, y ningun campo agregado: el vector se
    lee componente a componente y cada uno se compara con su propio umbral.
    """

    escena_id: int
    esquema_id: int
    plan_hash: str
    invalidacion_num: int
    invalidacion_den: int
    canon_huerfano_num: int
    canon_huerfano_den: int
    inviabilidad_num: int
    inviabilidad_den: int
    densidad_num: int
    densidad_den: int
    fiable: bool | None = None
    definicion_version: int
    medido_en: str
