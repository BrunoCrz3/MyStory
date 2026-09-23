"""Contratos de `process/` (RI-02).

Sin `dict` sueltos cruzando capas: lo que entra y lo que sale es Pydantic. Los
dos esquemas con sufijo `Guardable` / `Guardado` son la frontera con el
repositorio, y existen para que `deriva.py` pueda hablar de proporciones sin
saber en que columnas acaban.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.process.models import (
    ComponenteDeDeriva,
    CuentaEn,
    MotivoDeIngrediente,
    OrigenDeVersion,
    TipoDeElemento,
    TipoDeRestriccion,
)


class _Esquema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --- Esquema y brief ------------------------------------------------------


class NuevoHito(_Esquema):
    """RF-PROC-13. El motivo no es documentacion: es la etiqueta.

    Los umbrales de deriva se calibran en modo sombra separando «el autor
    replanifico en las siguientes k escenas» de «no lo hizo». Un hito sin motivo
    deja el dato sin la mitad que lo hace utilizable.
    """

    motivo: str


class NuevaRestriccion(_Esquema):
    """Lo que la escena no puede cambiar sin replanificar.

    Los campos cotejables --`personaje_id`, `lugar_id`, `hecho_id`, `valor`--
    son opcionales porque la ontologia no los exige, y su ausencia tiene precio
    declarado: una restriccion que solo trae prosa no se puede comprobar contra
    el snapshot, asi que ni invalida ni se adelanta. Cuenta en el denominador y
    en nada mas.
    """

    tipo: TipoDeRestriccion
    enunciado: str
    alcance: str | None = None
    personaje_id: int | None = None
    lugar_id: int | None = None
    hecho_id: int | None = None
    valor: str | None = None


class NuevoBrief(_Esquema):
    escena_id: int
    estado_de_entrada: str
    encargo: str | None = None
    restricciones: list[NuevaRestriccion] = []


class BriefCompleto(_Esquema):
    """El brief con lo que cuelga de el. Es lo que ve el redactor."""

    id: int
    escena_id: int
    estado_de_entrada: str
    encargo: str | None = None
    restricciones: list[NuevaRestriccion] = []


class EsquemaDeclarado(_Esquema):
    """Lo que el plan declara del futuro, y cuanto declara.

    RF-PROC-01 pide que el esquema materialice las restricciones de las escenas
    `planificada` aun no escritas, no solo la de la proxima: sin ellas la deriva
    no tiene denominador. Esta vista es donde se ve si se ha hecho.
    """

    plan_hash: str
    restricciones_futuras: int
    escenas_planificadas: int
    hito_vigente: int | None = None
    coincide_con_el_hito: bool


# --- Generacion -----------------------------------------------------------


class NuevoRegistro(_Esquema):
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


class PeticionDeBorrador(_Esquema):
    """Lo que el autor manda para que el redactor escriba.

    Las entidades y los personajes presentes son del brief y no del texto: la
    politica de recuperacion filtra por lo que el brief declara, no por
    similitud generica.
    """

    personajes_presentes: list[int] = []
    guia_de_estilo: str | None = None
    semilla: str | None = None


class PeticionDeAceptacion(_Esquema):
    """La firma del autor sobre una version concreta.

    No lleva casilla de «lo he editado»: una casilla se marca sola. Si la
    version entra en `training_samples` lo decide quien dejo el texto, que es un
    dato y no una declaracion (A-46).
    """

    version: int


class NuevaVersionDelAutor(_Esquema):
    """La edicion a mano. Es lo unico que hace entrar una escena en el banco."""

    texto: str


class Aceptacion(_Esquema):
    escena_id: int
    version: int
    entro_en_el_banco: bool
    motivo: str


class PasoSugerido(_Esquema):
    """Lo que el orquestador decide leyendo el estado persistido de la escena."""

    escena_id: int
    estado: str
    paso: str
    iteraciones_de_revision: int
    max_iteraciones_revision: int | None = None


# --- Banco de ejemplos ----------------------------------------------------


class NuevaMuestra(_Esquema):
    escena_id: int
    version_id: int
    brief: str
    contexto: str
    texto_aceptado: str


# --- Deriva ---------------------------------------------------------------


class IngredienteGuardado(_Esquema):
    componente: ComponenteDeDeriva
    tipo_elemento: TipoDeElemento
    elemento_id: int
    cuenta_en: CuentaEn
    motivo: MotivoDeIngrediente
    hecho_id: int | None = None


class MedidaGuardable(_Esquema):
    invalidacion_num: int
    invalidacion_den: int
    canon_huerfano_num: int
    canon_huerfano_den: int
    inviabilidad_num: int
    inviabilidad_den: int
    densidad_num: int
    densidad_den: int
    fiable: bool | None
    definicion_version: int
    ingredientes: list[IngredienteGuardado] = []


class Componente(_Esquema):
    numerador: int
    denominador: int
    valor: float
    umbral: float | None = None
    supera_el_umbral: bool | None = None


class VectorDeDeriva(_Esquema):
    """El vector leido, componente a componente.

    Sin agregado escalar: comparar un vector contra un solo numero seria perder
    justo la informacion por la que es un vector. Y `fiable` va al lado porque
    una deriva baja con densidad baja no es una novela sana, es un plan que no
    dice nada.
    """

    escena_id: int
    plan_hash: str
    definicion_version: int
    componentes: dict[ComponenteDeDeriva, Componente]
    densidad: Componente
    fiable: bool | None = None
    medido_en: str


class VersionConTraza(_Esquema):
    """RNF-05, RNF-06, P-24, P-28: la trayectoria, consultable a posteriori."""

    escena_id: int
    numero: int
    origen: OrigenDeVersion
    creada_en: str
    registro_id: int | None = None
    agente: str | None = None
    modelo: str | None = None
    huella_prompt: str | None = None
    huella_contexto: str | None = None
    huella_parametros: str | None = None
    semilla: str | None = None


__all__ = [
    "Aceptacion",
    "BriefCompleto",
    "Componente",
    "EsquemaDeclarado",
    "IngredienteGuardado",
    "MedidaGuardable",
    "NuevaMuestra",
    "NuevaVersionDelAutor",
    "NuevaRestriccion",
    "NuevoBrief",
    "NuevoHito",
    "NuevoRegistro",
    "PasoSugerido",
    "PeticionDeAceptacion",
    "PeticionDeBorrador",
    "VectorDeDeriva",
    "VersionConTraza",
]
