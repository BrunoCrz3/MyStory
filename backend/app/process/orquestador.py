"""El orquestador: la máquina de estados que decide qué corre a continuación (TO-012).

No hay agentes que conversen ni un agente que elija el paso siguiente: el orquestador lee el
estado de la novela y de sus capítulos, consulta la tabla de transiciones y ejecuta la acción.
Cada generación es una traza de Langfuse dentro de la sesión de su novela (RF-OBS-01).
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from functools import partial
from typing import Any

from app.commons.errores import ErrorDominio, LimiteDeIntentosAgotado
from app.commons.llm import ErrorModelo
from app.commons.llm.llamar import Consumo, acumular_en
from app.commons.recursos import Recursos
from app.commons.tiempo import ahora
from app.novel import service as novel
from app.policy.service import PolicyEngine
from app.process import repository
from app.process.aceptar import aceptar
from app.process.capitulo import ciclo_capitulo
from app.process.planificar import planificar
from app.process.transiciones import aplicar

_log = logging.getLogger("storymaker.orquestador")


class GeneracionDetenida(Exception):
    """Fin deliberado de una generación: se registra y la novela queda `Detenida`."""

    def __init__(self, motivo: str, detalle: str) -> None:
        super().__init__(detalle)
        self.motivo = motivo
        self.detalle = detalle


class Orquestador:
    def __init__(self, r: Recursos) -> None:
        self.r = r

    async def _trabajo(self, generacion_id: str) -> dict[str, Any]:
        t = await self.r.db.ejecutar(
            partial(repository.leer_trabajo_por_id, trabajo_id=generacion_id)
        )
        if t is None:
            raise LookupError(f"no existe el trabajo {generacion_id}")
        return t

    async def _actualizar(self, t: dict[str, Any], **cambios: Any) -> None:
        await self.r.db.ejecutar(
            partial(
                repository.actualizar_trabajo,
                novel_id=t["novel_id"],
                trabajo_id=t["id"],
                cambios=cambios,
            )
        )

    async def _mover_novela(self, t: dict[str, Any], accion: str) -> str:
        """Aplica una acción de la máquina de la novela a la obra y al trabajo, juntos."""

        def mover(con: sqlite3.Connection) -> str:
            actual = novel.estado_de_obra(con, novel_id=t["novel_id"])
            destino = aplicar("Novela", actual, accion)
            novel.fijar_estado_obra(con, novel_id=t["novel_id"], estado=destino)
            repository.actualizar_trabajo(
                con, novel_id=t["novel_id"], trabajo_id=t["id"], cambios={"estado": destino}
            )
            return destino

        return await self.r.db.en_transaccion(mover)

    async def _guardar_consumo(self, t: dict[str, Any], consumo: Consumo) -> None:
        await self._actualizar(
            t,
            tokens_consumidos=consumo.tokens,
            coste_usd=round(consumo.coste_usd, 6),
            intentos_infra=t["intentos_infra"] + consumo.reintentos_infra,
        )

    def _comprobar_topes(self, t: dict[str, Any], consumo: Consumo) -> None:
        """Coste y latencia por novela bajo umbral; superarlo detiene e informa (RNF-13)."""
        coste = self.r.config.umbrales.coste
        if consumo.coste_usd > coste.coste_maximo_novela:
            raise GeneracionDetenida(
                "error-interno",
                f"el coste ({consumo.coste_usd:.4f} USD) supera coste.coste_maximo_novela "
                f"({coste.coste_maximo_novela})",
            )
        iniciada = datetime.fromisoformat(t["iniciada_en"].replace("Z", "+00:00"))
        transcurrido = (datetime.now(UTC) - iniciada).total_seconds()
        if transcurrido > coste.latencia_maxima_novela:
            raise GeneracionDetenida(
                "error-interno",
                f"la generación lleva {transcurrido:.0f} s y coste.latencia_maxima_novela es "
                f"{coste.latencia_maxima_novela}",
            )

    async def ejecutar(self, generacion_id: str) -> None:
        t = await self._trabajo(generacion_id)
        consumo = Consumo(coste_usd=t["coste_usd"], tokens_entrada=t["tokens_consumidos"])
        with (
            acumular_en(consumo),
            self.r.trazador.traza(
                "generacion",
                novel_id=t["novel_id"],
                metadata={"generacion_id": t["id"], "tipo": t["tipo"]},
            ) as traza,
        ):
            await self._actualizar(t, traza_langfuse_id=traza.traza_id)
            try:
                await self._inicial(t, consumo)
            except GeneracionDetenida as d:
                await self._detener(t, d.motivo, d.detalle)
            except LimiteDeIntentosAgotado as e:
                await self._detener(t, e.slug, str(e))
            except ErrorDominio as e:
                _log.error("generación %s detenida por %s", t["id"], e.slug)
                await self._detener(t, e.slug, str(e))
            except ErrorModelo as e:
                # Reintentos de infraestructura agotados, contexto que no cabe, rechazo del
                # modelo: el catálogo no tiene un tipo propio y se informa como error interno,
                # con el motivo en el audit log.
                _log.error("generación %s detenida: %s", t["id"], type(e).__name__)
                await self._detener(t, "error-interno", f"{type(e).__name__}: {e}")
            finally:
                await self._guardar_consumo(t, consumo)

    async def _inicial(self, t: dict[str, Any], consumo: Consumo) -> None:
        novel_id, version = t["novel_id"], t["version_objetivo"]
        estado = await self.r.db.ejecutar(partial(novel.estado_de_obra, novel_id=novel_id))
        if estado == "Configurando":
            await self._mover_novela(t, "Planificar")
            estado = "Planificando"
        if estado == "Planificando":
            await planificar(self.r, novel_id=novel_id, version=version)
            self._comprobar_topes(t, consumo)
            await self._mover_novela(t, "FijarEsquema")

        total = await self.r.db.ejecutar(partial(novel.total_capitulos, novel_id=novel_id))
        for numero in range(1, total + 1):
            cap = await self.r.db.ejecutar(
                partial(novel.capitulo_en_curso, novel_id=novel_id, numero=numero, version=version)
            )
            if cap is None or cap.estado == "Aceptado":
                continue
            await self._actualizar(t, capitulo_actual=numero)
            resultado = await ciclo_capitulo(
                self.r, novel_id=novel_id, version=version, numero=numero
            )
            if resultado.accion != "aceptar":
                raise GeneracionDetenida(
                    resultado.detenida_por or "limite-de-intentos-agotado",
                    f"el capítulo {numero} no convergió ({resultado.accion})",
                )
            await aceptar(
                self.r,
                novel_id=novel_id,
                version=version,
                numero=numero,
                resultado=resultado,
                generacion_id=t["id"],
            )
            await self._guardar_consumo(t, consumo)
            self._comprobar_topes(t, consumo)

        await self._mover_novela(t, "CerrarEscritura")
        await self._cerrar(t)

    async def _cerrar(self, t: dict[str, Any]) -> None:
        """Hasta que exista el gate de publicación (P25), la generación termina en `Validando`."""
        await self._actualizar(t, estado_cola="terminado", terminada_en=ahora())

    async def _detener(self, t: dict[str, Any], motivo: str, detalle: str) -> None:
        motor = PolicyEngine(self.r.config)

        def detener(con: sqlite3.Connection) -> None:
            actual = novel.estado_de_obra(con, novel_id=t["novel_id"])
            destino = aplicar("Novela", actual, "Detener")
            novel.fijar_estado_obra(con, novel_id=t["novel_id"], estado=destino)
            repository.actualizar_trabajo(
                con,
                novel_id=t["novel_id"],
                trabajo_id=t["id"],
                cambios={
                    "estado": destino,
                    "estado_cola": "terminado",
                    "detenida_por": motivo,
                    "terminada_en": ahora(),
                },
            )
            motor.registrar_detencion(
                con,
                novel_id=t["novel_id"],
                generacion_id=t["id"],
                motivo=motivo,
                detalle={"detalle": detalle[:2000]},
            )

        await self.r.db.en_transaccion(detener)
