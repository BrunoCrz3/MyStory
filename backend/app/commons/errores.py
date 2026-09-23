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


class BorradorNoHigienico(ReglaDelDominioIncumplida):
    """A-47, RF-QUA-06. La puerta corre antes de la critica y antes del punto
    unico de promocion: un borrador que la falla no entra al ciclo."""

    codigo_por_defecto = "borrador_no_higienico"


class DimensionSinValidador(ErrorDeArranque):
    """RF-QUA-02: una dimension declarada que ninguna validacion puntua.

    Es de arranque y no de dominio a proposito: un informe al que le falta una
    dimension no es una peticion mal hecha, es el sistema mal montado.
    """

    codigo_por_defecto = "dimension_sin_validador"


class AceptacionSoloDelAutor(ErrorDeDominio):
    """RF-PROC-07, P-19. El autor humano es el unico que acepta una escena.

    Es 403 y no 422: lo que falla no es la forma de la peticion sino quien la
    hace. Es el ultimo cortafuegos de la resistencia a inyeccion, y por eso no
    se relaja para agilizar nada.
    """

    http = 403
    codigo_por_defecto = "aceptacion_solo_del_autor"


class PlanCambiadoSinHito(ConflictoDeEstado):
    """RF-PROC-13. El conjunto de restricciones futuras cambio y nadie lo
    registro: sin motivo no hay etiqueta con la que calibrar la deriva, y el
    acumulado pierde su ancla."""

    codigo_por_defecto = "plan_cambiado_sin_hito"


class DerivaSoloDeEscenaAceptada(ConflictoDeEstado):
    """RF-PROC-08. La deriva se mide contra el canon en `t`, y el canon solo
    existe tras consolidar una escena aceptada."""

    codigo_por_defecto = "deriva_solo_de_escena_aceptada"


class EscenaSeAdelantaAlPlan(ReglaDelDominioIncumplida):
    """P-41, RF-PROC-11. La escena descubre *como*, no *hacia donde*: satisfacer
    el destino de un brief posterior es cambiar el plan desde dentro de una
    escena, que es justo lo que la replanificacion existe para hacer fuera."""

    codigo_por_defecto = "escena_se_adelanta_al_plan"


class BriefSinRestriccionDeDestino(ReglaDelDominioIncumplida):
    """RF-PROC-01. Un brief sin destino no acota nada: la escena descubriria
    tambien hacia donde va, y la deriva se quedaria sin denominador."""

    codigo_por_defecto = "brief_sin_restriccion_de_destino"
