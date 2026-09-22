"""Contratos de entrada de `novel/` (RI-02).

Todo lo que entra por HTTP es un modelo Pydantic v2: no cruzan `dict` sueltos
entre capas. Lo que sale son las clases de `models.py`, que son la ontologia.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.novel.models import EstadoDeEscena


class _Nuevo(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NuevaObra(_Nuevo):
    titulo: str | None = None
    premisa: str
    genero: str
    extension_objetivo: int | None = None
    publico: str | None = None


class NuevaParte(_Nuevo):
    obra_id: int
    orden: int
    funcion_dramatica: str
    punto_de_giro: str | None = None


class NuevoCapitulo(_Nuevo):
    parte_id: int
    orden: int
    pov_dominante_id: int | None = None
    gancho_de_cierre: str | None = None


class NuevaEscena(_Nuevo):
    capitulo_id: int
    orden: int
    objetivo: str | None = None
    conflicto: str | None = None
    resultado: str | None = None
    personaje_pov_id: int | None = None
    lugar_id: int | None = None
    momento: str | None = None
    estado_de_entrada: str | None = None
    estado_de_salida: str | None = None


class NuevoBeat(_Nuevo):
    escena_id: int
    orden: int
    valor_inicial: str | None = None
    valor_final: str | None = None


class NuevoPersonaje(_Nuevo):
    nombre: str
    deseo: str | None = None
    necesidad: str | None = None
    herida: str | None = None
    rol_narrativo: str | None = None
    arco_id: int | None = None


class NuevaVoz(_Nuevo):
    personaje_id: int
    lexico: str | None = None
    registro: str | None = None
    sintaxis: str | None = None
    muletillas: str | None = None
    temas_recurrentes: str | None = None


class NuevoArco(_Nuevo):
    nombre: str
    estado_inicial: str | None = None
    puntos_de_giro: str | None = None
    estado_final: str | None = None


class NuevoHiloDeTrama(_Nuevo):
    nombre: str
    tipo: str
    pregunta_dramatica: str | None = None
    estado: str | None = None


class NuevoLugar(_Nuevo):
    nombre: str
    geografia: str | None = None
    atmosfera_sensorial: str | None = None
    reglas_propias: str | None = None


class NuevaFaccion(_Nuevo):
    nombre: str
    objetivo: str | None = None
    recursos: str | None = None


class NuevoArtefacto(_Nuevo):
    nombre: str
    propiedades: str | None = None
    poseedor_actual_id: int | None = None
    deuda_narrativa: str | None = None


class NuevoNovum(_Nuevo):
    nombre: str
    mecanismo: str
    limites: str
    consecuencias_en_cascada: str | None = None


class NuevaReglaDelMundo(_Nuevo):
    novum_id: int
    enunciado: str
    alcance: str | None = None
    excepciones_declaradas: str | None = None


class NuevoTerminoCanonico(_Nuevo):
    forma: str
    definicion: str | None = None
    novum_id: int | None = None
    primera_aparicion_id: int | None = None
    variantes_prohibidas: str | None = None


class NuevoTema(_Nuevo):
    nombre: str
    enunciado: str | None = None


class NuevoMotivo(_Nuevo):
    nombre: str
    forma: str | None = None
    evolucion: str | None = None


class NuevaVozNarrativa(_Nuevo):
    obra_id: int
    persona: str | None = None
    tiempo_verbal: str | None = None
    distancia: str | None = None
    focalizacion: str | None = None
    ratio_escena_resumen: str | None = None


class NuevoEvento(_Nuevo):
    que_ocurre: str
    momento_en_la_fabula: str | None = None
    duracion: str | None = None


class NuevoObjetivo(_Nuevo):
    personaje_id: int
    enunciado: str
    alcance: str | None = None
    tipo: str | None = None
    estado: str | None = None


class NuevaTransicion(_Nuevo):
    destino: EstadoDeEscena
