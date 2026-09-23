"""Excepciones propias del sistema.

Dos familias, y la diferencia importa. Un `ErrorDeArranque` no tiene codigo HTTP
porque no hay nadie al otro lado: la instancia no llega a servir. Un
`ErrorDeDominio` si lo tiene, y lo declara el propio error en vez de un mapa
central: el punto ciego que `docs/verification.md` anota en A-36 es justo ese
mapa, porque una excepcion nueva que nadie registra sale como 500.
"""

from __future__ import annotations

from typing import ClassVar


class ErrorDeMyStory(Exception):
    """Raiz de todo error propio. Nunca se lanza directamente."""

    codigo_por_defecto: ClassVar[str] = "error"

    def __init__(self, mensaje: str, *, codigo: str | None = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo or self.codigo_por_defecto


class ErrorDeArranque(ErrorDeMyStory):
    """Falla en voz alta antes de servir nada. No se traduce a HTTP."""

    codigo_por_defecto = "arranque_invalido"


class ConfiguracionInvalida(ErrorDeArranque):
    codigo_por_defecto = "configuracion_invalida"


class UmbralAusente(ErrorDeArranque):
    """RF-QUA-05: falta un umbral que se usa para cerrar el paso."""

    codigo_por_defecto = "umbral_ausente"


class MigracionEditada(ErrorDeArranque):
    """AGENTS.md regla 5: una migracion commiteada no se edita nunca."""

    codigo_por_defecto = "migracion_editada"


class MigracionMalNumerada(ErrorDeArranque):
    codigo_por_defecto = "migracion_mal_numerada"


class ErrorDeDominio(ErrorDeMyStory):
    """Se traduce a HTTP en el handler central de `commons/http.py` (RI-04)."""

    http: ClassVar[int] = 400
    codigo_por_defecto = "error_de_dominio"


class RecursoNoEncontrado(ErrorDeDominio):
    http = 404
    codigo_por_defecto = "recurso_no_encontrado"


class ConflictoDeEstado(ErrorDeDominio):
    http = 409
    codigo_por_defecto = "conflicto_de_estado"


class TransicionInvalida(ConflictoDeEstado):
    """Una transicion que el diagrama de estados no dibuja."""

    codigo_por_defecto = "transicion_invalida"


class PresupuestoExcedido(ErrorDeDominio):
    """AGENTS.md regla 3: un ensamblado que no cabe falla en voz alta."""

    http = 422
    codigo_por_defecto = "presupuesto_excedido"


class ReglaDelDominioIncumplida(ErrorDeDominio):
    """Lo que se pide es coherente con el esquema pero no con la obra."""

    http = 422
    codigo_por_defecto = "regla_incumplida"


class NovumSinLimites(ReglaDelDominioIncumplida):
    """A-51: sin limites declarados, RF-QUA-01 no tiene contra que medir."""

    codigo_por_defecto = "novum_sin_limites"


class NovumSinRegla(ReglaDelDominioIncumplida):
    """A-51: todo `Novum` impone al menos una `Regla del mundo`."""

    codigo_por_defecto = "novum_sin_regla"


class ActoIncompleto(ReglaDelDominioIncumplida):
    """A-51: una `Parte / Acto` sin funcion dramatica ni punto de giro."""

    codigo_por_defecto = "acto_incompleto"


class CanonSoloAlAceptar(ReglaDelDominioIncumplida):
    """A-27, A-28, RF-CANON-07. El canon solo cambia al consolidar una escena
    aceptada; un borrador rechazado no deja rastro."""

    codigo_por_defecto = "canon_solo_al_aceptar"


class HechoSinAnclaje(ReglaDelDominioIncumplida):
    """RF-CANON-11, A-48. Un hecho cuyos terminos no estan en la escena que lo
    establece no esta atado a la prosa de la que salio."""

    codigo_por_defecto = "hecho_sin_anclaje"


class PromesaSinEscenaDePago(ReglaDelDominioIncumplida):
    codigo_por_defecto = "promesa_sin_escena_de_pago"


class PromesaPagadaAntesDeAbrirse(ReglaDelDominioIncumplida):
    """P-45, RF-CANON-13. El pago necesita un setup anterior."""

    codigo_por_defecto = "promesa_pagada_antes_de_abrirse"


class IndiceDesactualizado(ErrorDeArranque):
    """A-42, RF-CTX-10. Vectores de modelos distintos no son comparables, y
    mezclarlos no da error: da una recuperacion que devuelve lo que no toca."""

    codigo_por_defecto = "indice_desactualizado"


class DimensionDeEmbeddingInvalida(ReglaDelDominioIncumplida):
    """El vector no tiene la dimension que declara `config/thresholds.yaml`."""

    codigo_por_defecto = "dimension_de_embedding_invalida"
