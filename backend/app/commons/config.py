"""Lectura de `config/thresholds.yaml`, fuente unica de cifras (RNF-14, A-40).

Ningun campo tiene valor por defecto. Es deliberado: un defecto en el codigo es
una cifra escrita suelta, y entonces el fichero deja de ser la fuente unica.
Si falta una clave, el arranque falla en voz alta.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from app.commons.errores import ConfiguracionInvalida, UmbralAusente

VARIABLE_DE_ENTORNO = "MYSTORY_UMBRALES"


def raiz_del_repositorio() -> Path:
    return Path(__file__).resolve().parents[3]


def ruta_por_defecto_de_umbrales() -> Path:
    declarada = os.environ.get(VARIABLE_DE_ENTORNO)
    if declarada:
        return Path(declarada)
    return raiz_del_repositorio() / "config" / "thresholds.yaml"


class _Bloque(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Capas(_Bloque):
    invariante: int
    estructural: int
    estado: int
    local: int
    recuperado: int
    estilo: int
    anticontexto: int
    margen: int


class Contexto(_Bloque):
    total: int
    capas: Capas
    degradacion: list[str]
    anticontexto_ventana_escenas: int | None
    tokens_por_mil_caracteres: int


class EnVuelo(_Bloque):
    total: int


class UmbralDeDeriva(_Bloque):
    invalidacion: float | None
    canon_huerfano: float | None
    inviabilidad_pago: float | None


class Deriva(_Bloque):
    umbral: UmbralDeDeriva
    densidad_declaracion_minima: float | None


class Backoff(_Bloque):
    base_segundos: float | None
    factor: float | None
    jitter: bool


class Orquestacion(_Bloque):
    max_iteraciones_revision: int | None
    max_intentos_trabajo: int | None
    backoff: Backoff


class Medicion(_Bloque):
    cerrar_el_paso: bool


class Calidad(_Bloque):
    consistencia_factica: float | None
    consistencia_temporal: float | None
    consistencia_espacial: float | None
    consistencia_epistemica: float | None
    plausibilidad_especulativa: float | None
    distintividad_de_voz: float | None
    calidad_de_prosa: float | None
    mostrar_vs_contar: float | None
    integridad_de_pov: float | None
    causalidad: float | None
    ritmo: float | None
    carga_expositiva: float | None
    originalidad: float | None
    cumplimiento_del_brief: float | None


class Embeddings(_Bloque):
    modelo: str
    version: str | None
    dimension: int | None


class Recuperacion(_Bloque):
    max_fragmentos: int | None


class Continuidad(_Bloque):
    escenas_sin_avanzar_arco: int | None
    escenas_sin_avanzar_hilo: int | None
    promesas_pendientes_max: int | None
    similitud_escena_duplicada: float | None
    repeticion_descripcion_entidad: float | None
    deriva_estilo_vs_linea_base: float | None
    densidad_acto_final: float | None


class Higiene(_Bloque):
    desviacion_longitud_escena: float | None


class Validadores(_Bloque):
    precision_minima: float | None
    cobertura_minima: float | None


class ModeloDeGeneracion(_Bloque):
    id: str
    timeout_segundos: float


class Umbrales(_Bloque):
    version: int
    contexto: Contexto
    en_vuelo: EnVuelo
    deriva: Deriva
    orquestacion: Orquestacion
    medicion: Medicion
    calidad: Calidad
    embeddings: Embeddings
    recuperacion: Recuperacion
    continuidad: Continuidad
    higiene: Higiene
    validadores: Validadores
    modelo: ModeloDeGeneracion

    def para_cerrar_el_paso(self, clave: str) -> float:
        """Devuelve un umbral, o falla si es `null`.

        Pedir un umbral para cerrar el paso es lo que hace fallar el arranque
        (RF-QUA-05). Medir y registrar sin suspender no pasa por aqui.
        """
        valor: Any = self
        for tramo in clave.split("."):
            if isinstance(valor, BaseModel) and tramo in type(valor).model_fields:
                valor = getattr(valor, tramo)
            else:
                raise UmbralAusente(f"no existe el umbral '{clave}'")
        if valor is None:
            raise UmbralAusente(
                f"el umbral '{clave}' esta en null y se ha pedido para cerrar el paso"
            )
        return float(valor)


def cargar_umbrales(ruta: Path | None = None) -> Umbrales:
    fichero = ruta or ruta_por_defecto_de_umbrales()
    if not fichero.is_file():
        raise ConfiguracionInvalida(f"no existe el fichero de umbrales: {fichero}")
    try:
        crudo = yaml.safe_load(fichero.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ConfiguracionInvalida(f"{fichero} no es YAML valido: {error}") from error
    try:
        return Umbrales.model_validate(crudo)
    except ValidationError as error:
        raise ConfiguracionInvalida(f"{fichero} no cuadra con el esquema: {error}") from error


def verificar_arranque(umbrales: Umbrales) -> None:
    """A-41, RF-QUA-05.

    Con `medicion.cerrar_el_paso` en `false` la instancia mide y registra sin
    suspender, y por eso arranca con los umbrales en null. En `true` no puede:
    un umbral ausente que decide seria una decision inventada.
    """
    if not umbrales.medicion.cerrar_el_paso:
        return
    ausentes = [
        nombre
        for nombre in type(umbrales.calidad).model_fields
        if getattr(umbrales.calidad, nombre) is None
    ]
    if ausentes:
        raise UmbralAusente(
            "medicion.cerrar_el_paso es true y faltan umbrales de calidad: " + ", ".join(ausentes)
        )
