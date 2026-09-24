"""Forma de `config/thresholds.yaml` y `config/models.yaml`.

Los modelos son estrictos (`extra="forbid"`): una clave mal escrita es un error de arranque,
no un umbral que se ignora en silencio. Los tipos distinguen lo que cierra el paso siempre
—entero o real obligatorio— de lo que solo lo cierra fuera de la fase de medición, que
admite `null` (TO-036, A-03).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Obra(_Estricto):
    capitulos: int


class Capitulo(_Estricto):
    longitud_min_palabras: int
    longitud_max_palabras: int


class Capas(_Estricto):
    invariante: int
    estructural: int
    estado: int
    local: int
    recuperado: int
    estilo: int
    anticontexto: int
    margen: int


CapaDegradable = Literal["recuperado", "estilo", "local", "estado"]


class Contexto(_Estricto):
    total: int
    capas: Capas
    degradacion: list[CapaDegradable]
    anticontexto_ventana_capitulos: int


class EnVuelo(_Estricto):
    total: int


class Replanificacion(_Estricto):
    solo_capitulos_pendientes: bool


class Backoff(_Estricto):
    base_segundos: float
    factor: float
    jitter: bool


class Orquestacion(_Estricto):
    max_intentos_capitulo: int
    max_intentos_trabajo: int
    backoff: Backoff
    timeout_llamada_segundos: float
    intervalo_sondeo_segundos: int


class Normalizacion(_Estricto):
    minusculas: bool
    quitar_acentos: bool
    quitar_signos: bool
    plurales: bool
    variantes_simples: bool


class PerfilGuardrail(_Estricto):
    edad_maxima_infantil: int
    edad_maxima_adolescente: int


class Guardrail(_Estricto):
    niveles: list[Literal["global", "perfil", "novela"]]
    normalizacion: Normalizacion
    perfil: PerfilGuardrail
    max_reescrituras: int


class Medicion(_Estricto):
    cerrar_el_paso: bool


class Calidad(_Estricto):
    """Umbrales con score. Los `| None` solo cierran el paso fuera de la fase de medición."""

    consistencia_factica: float | None
    calidad_prosa: float | None
    integridad_pov: float | None
    cumplimiento_brief: float | None
    personalizacion_natural: float | None
    reconocibilidad: float | None
    adecuacion_tono: float | None
    coherencia_personajes: float | None
    ritmo: float | None
    cierre_arco: float | None
    # Cuentan hasta cero y cierran el paso siempre (PO-1, PO-2).
    invencion_destinatario: int
    temas_excluidos: int
    legibilidad_inflesz_minimo: float | None
    legibilidad_inflesz_minimo_infantil: float | None


class Continuidad(_Estricto):
    promesas_pendientes_al_cerrar: int
    capitulos_sin_avanzar_arco: int | None
    capitulos_sin_avanzar_hilo: int | None
    similitud_capitulo_duplicado: float | None
    repeticion_descripcion_entidad: float | None
    deriva_estilo_vs_linea_base: float | None
    dispersion_elementos_personalizados: float | None
    varianza_longitud_entre_capitulos: float | None


class Prosa(_Estricto):
    longitud_ngrama: int
    repeticion_ngramas: int | None
    densidad_muletillas: float | None
    densidad_cliches: float | None
    densidad_adverbios: float | None
    varianza_longitud_frase: float | None


class Validadores(_Estricto):
    precision_minima: float
    cobertura_minima: float
    cobertura_tests_minima: float
    acuerdo_minimo_judge_humano: float
    tolerancia_estabilidad_judge: float


class PrecioModelo(_Estricto):
    entrada: float
    salida: float


class Coste(_Estricto):
    latencia_maxima_novela: float
    coste_maximo_novela: float
    precio_usd_por_millon: dict[str, PrecioModelo] = {}


Rol = Literal["entrevistador", "planificador", "redactor", "editor", "judge", "extractor"]
ROLES: tuple[Rol, ...] = (
    "entrevistador",
    "planificador",
    "redactor",
    "editor",
    "judge",
    "extractor",
)


class MaxTokensPorRol(_Estricto):
    entrevistador: int
    planificador: int
    redactor: int
    editor: int
    judge: int
    extractor: int


class ClaudeCode(_Estricto):
    caracteres_por_token: float = Field(gt=0)
    margen_estimacion: float = Field(ge=1)


class Modelo(_Estricto):
    max_tokens_por_rol: MaxTokensPorRol
    claude_code: ClaudeCode


class Formal(_Estricto):
    gate_activo: bool
    lean_incremental: bool
    lean_timeout_segundos: float | None


class Export(_Estricto):
    tolerancia_recuento_palabras: float


class ModeloFormal(_Estricto):
    capitulos: int
    reintentos: int


class Recuperacion(_Estricto):
    max_fragmentos: int


class Regeneracion(_Estricto):
    similitud_hecho_candidato: float


class Embeddings(BaseModel):
    """Inactivo en v1 (TO-015): se conserva la plantilla y no se valida."""

    model_config = ConfigDict(extra="allow", frozen=True)


class Umbrales(_Estricto):
    version: int
    obra: Obra
    capitulo: Capitulo
    contexto: Contexto
    en_vuelo: EnVuelo
    replanificacion: Replanificacion
    orquestacion: Orquestacion
    guardrail: Guardrail
    medicion: Medicion
    calidad: Calidad
    continuidad: Continuidad
    prosa: Prosa
    validadores: Validadores
    coste: Coste
    modelo: Modelo
    formal: Formal
    export: Export
    modelo_formal: ModeloFormal
    recuperacion: Recuperacion
    regeneracion: Regeneracion | None = None
    embeddings: Embeddings | None = None


Effort = Literal["low", "medium", "high", "xhigh", "max"]


class ModeloDeRol(_Estricto):
    id: str
    effort: Effort


class Roles(_Estricto):
    entrevistador: ModeloDeRol
    planificador: ModeloDeRol
    redactor: ModeloDeRol
    editor: ModeloDeRol
    judge: ModeloDeRol
    extractor: ModeloDeRol

    def de(self, rol: Rol) -> ModeloDeRol:
        modelo: ModeloDeRol = getattr(self, rol)
        return modelo


Proveedor = Literal["api", "claude_code"]


class Modelos(_Estricto):
    version: int
    proveedor: Proveedor
    roles: Roles


class Config(_Estricto):
    umbrales: Umbrales
    modelos: Modelos

    def max_tokens(self, rol: Rol) -> int:
        valor: int = getattr(self.umbrales.modelo.max_tokens_por_rol, rol)
        return valor

    def coste_usd(self, modelo: str, tokens_entrada: int, tokens_salida: int) -> float:
        precio = self.umbrales.coste.precio_usd_por_millon[modelo]
        return (tokens_entrada * precio.entrada + tokens_salida * precio.salida) / 1_000_000
