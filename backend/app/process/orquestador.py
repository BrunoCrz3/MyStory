"""El orquestador: la máquina de estados que decide qué corre a continuación (TO-012).

No hay agentes que conversen ni un agente que elija el paso siguiente: el orquestador lee el
estado de la novela y de sus capítulos, consulta la tabla de transiciones y ejecuta la acción.
Cada generación es una traza de Langfuse dentro de la sesión de su novela (RF-OBS-01).
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import UTC, datetime
from functools import partial
from typing import Any

from app.canon import service as canon
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
from app.process.service import Publicador, VeredictoGate
from app.process.transiciones import aplicar

_log = logging.getLogger("storymaker.orquestador")

# Estados de un capítulo que solo existen mientras un proceso lo está trabajando.
_A_MEDIAS = ("Escribiendo", "Validando", "Reescribiendo")


class GeneracionDetenida(Exception):
    """Fin deliberado de una generación: se registra y la novela queda `Detenida`."""

    def __init__(self, motivo: str, detalle: str) -> None:
        super().__init__(detalle)
        self.motivo = motivo
        self.detalle = detalle


class GateEnRojo(GeneracionDetenida):
    """El gate de publicación no pasa: la candidata queda `rechazada` (RF-QUA-03, TO-045).

    El editor corrige capítulos, no la novela entera: arreglar un fallo del gate —una promesa
    sin pagar— exige reescribir capítulos ya aceptados, y eso es el retcon de F4. Así que la
    generación vuelve al editor y se detiene con los validadores fallidos en el audit log
    (A-47, A-79).
    """

    def __init__(self, fallidos: list[VeredictoGate]) -> None:
        super().__init__(
            "error-interno",
            "el gate de publicación falló: "
            + "; ".join(f"{v.nombre}: {v.detalle}" for v in fallidos),
        )
        self.fallidos = fallidos


class Orquestador:
    def __init__(self, r: Recursos, publicador: Publicador) -> None:
        self.r = r
        self.publicador = publicador

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
                if t["tipo"] == "dirigida":
                    await self._dirigida(t, consumo)
                else:
                    await self._inicial(t, consumo)
            except GateEnRojo as g:
                await self._detener(t, g.motivo, g.detalle, devolver_al_editor=True)
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

    async def estado_inicial(self, novel_id: str, version: int) -> list[int]:
        """Reanudación desde el checkpoint (RF-PROC-06, TO-023).

        Los aceptados se quedan como están y el bucle los salta; el capítulo que el proceso
        anterior dejó a medias vuelve a `Pendiente` escribiendo el estado directamente, porque
        su borrador murió con el proceso y ningún estado intermedio es reanudable. No hay
        arista en la tabla de transiciones, y es a propósito: no es un paso de la historia.
        """
        normalizados = await self.r.db.en_transaccion(
            partial(
                novel.devolver_a_pendiente, novel_id=novel_id, version=version, estados=_A_MEDIAS
            )
        )
        if normalizados:
            _log.warning("novela %s: capítulos %s vuelven a Pendiente", novel_id, normalizados)
        return normalizados

    async def _dirigida(self, t: dict[str, Any], consumo: Consumo) -> None:
        """Regeneración dirigida (RF-VER-08, D-05): reescribe **solo** los capítulos del análisis
        de impacto y publica la versión nueva; la anterior no se toca.

        Cada capítulo afectado tiene una fila nueva en la versión objetivo; la de la versión
        publicada se queda `Obsoleto` e intacta, y los no afectados son la misma fila en las dos
        versiones. Antes de reescribir, lo que la fila vieja establecía o usaba se retira del
        canon desde la versión nueva, y el redactor recibe el cambio como aviso. Reanudable:
        los capítulos ya aceptados en la versión objetivo se saltan.
        """
        novel_id, version = t["novel_id"], t["version_objetivo"]
        await self.estado_inicial(novel_id, version)
        estado = await self.r.db.ejecutar(partial(novel.estado_de_obra, novel_id=novel_id))
        if estado == "Publicada":
            await self._mover_novela(t, "Regenerar")
        aviso = await self._aviso(t)
        afectados: list[int] = json.loads(t["capitulos_a_regenerar"] or "[]")
        for numero in afectados:
            cap = await self.r.db.ejecutar(
                partial(novel.capitulo_en_curso, novel_id=novel_id, numero=numero, version=version)
            )
            if cap is not None and cap.estado == "Aceptado":
                continue
            if cap is None:
                await self.r.db.en_transaccion(
                    partial(
                        self._preparar_reescritura,
                        novel_id=novel_id,
                        numero=numero,
                        version=version,
                    )
                )
            await self._actualizar(t, capitulo_actual=numero)
            resultado = await ciclo_capitulo(
                self.r, novel_id=novel_id, version=version, numero=numero, aviso=aviso
            )
            if resultado.accion != "aceptar":
                raise GeneracionDetenida(
                    resultado.detenida_por or "limite-de-intentos-agotado",
                    f"el capítulo {numero} no convergió al reescribirlo ({resultado.accion})",
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

        estado = await self.r.db.ejecutar(partial(novel.estado_de_obra, novel_id=novel_id))
        if estado == "Regenerando":
            await self._mover_novela(t, "CerrarRegeneracion")
        await self._cerrar(t)

    @staticmethod
    def _preparar_reescritura(
        con: sqlite3.Connection, *, novel_id: str, numero: int, version: int
    ) -> None:
        """La fila nueva del capítulo en la versión objetivo, y el canon de la vieja retirado
        desde esa versión, en una transacción."""
        anterior = novel.capitulo_vigente(con, novel_id=novel_id, numero=numero, version=version)
        if anterior is not None:
            canon.retirar_capitulo(con, novel_id=novel_id, capitulo_id=anterior, version=version)
        novel.crear_capitulo(con, novel_id=novel_id, numero=numero, version=version)

    async def _aviso(self, t: dict[str, Any]) -> str | None:
        if not t["solicitud_id"]:
            return None
        cambio = await self.r.db.ejecutar(
            partial(canon.retcon_de, novel_id=t["novel_id"], solicitud_id=t["solicitud_id"])
        )
        if cambio is None:
            return None
        viejo, nuevo = cambio
        return (
            "Este capítulo se reescribe porque el lector cambió un hecho de la novela: "
            f"ahora es verdad que «{nuevo}», en lugar de «{viejo}». Cuenta el capítulo con el "
            "hecho nuevo y conserva todo lo demás: su destino, sus personajes y su lugar."
        )

    async def _inicial(self, t: dict[str, Any], consumo: Consumo) -> None:
        novel_id, version = t["novel_id"], t["version_objetivo"]
        await self.estado_inicial(novel_id, version)
        estado = await self.r.db.ejecutar(partial(novel.estado_de_obra, novel_id=novel_id))
        if estado == "Configurando":
            await self._mover_novela(t, "Planificar")
            estado = "Planificando"
        if estado == "Planificando":
            # Un corte entre guardar el esquema y fijarlo no replanifica: el esquema ya está.
            if not await self.r.db.ejecutar(partial(repository.hay_esquema, novel_id=novel_id)):
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

        estado = await self.r.db.ejecutar(partial(novel.estado_de_obra, novel_id=novel_id))
        if estado == "Escribiendo":
            await self._mover_novela(t, "CerrarEscritura")
        await self._cerrar(t)

    async def _cerrar(self, t: dict[str, Any]) -> None:
        """La versión candidata, el gate sobre ella y, si pasa, la publicación (RF-VER-01,
        RF-QUA-03, RNF-19, TO-045).

        La candidata se escribe antes del gate porque `render_visual` tiene que pintarla: la
        lectura la pide por su número. Ninguna versión pasa a `publicada` sin que pasen todos
        los validadores; si falla uno, queda `rechazada` en la misma transacción que detiene la
        novela, y nunca es la vigente. Publicar y conservar van en una sola transacción: la
        reanudación nunca encuentra la novela en `Publicando`.
        """
        novel_id, version = t["novel_id"], t["version_objetivo"]

        def proponer(con: sqlite3.Connection) -> str:
            return self.publicador.proponer(
                con, novel_id=novel_id, version=version, generacion_id=t["id"]
            )

        await self.r.db.en_transaccion(proponer)
        with self.r.trazador.span("gate_publicacion", metadata={"version": version}):
            veredictos = await self.r.db.ejecutar(
                partial(self.publicador.gate, novel_id=novel_id, version=version)
            )
            veredictos.append(
                await self.publicador.render_visual(novel_id=novel_id, version=version)
            )
            for v in veredictos:
                self.r.trazador.score(v.nombre, v.valor, comentario=v.detalle[:2000])
        fallidos = [v for v in veredictos if not v.pasa]
        if fallidos:
            raise GateEnRojo(fallidos)

        def publicar(con: sqlite3.Connection) -> None:
            actual = novel.estado_de_obra(con, novel_id=novel_id)
            destino = aplicar("Novela", aplicar("Novela", actual, "Publicar"), "Conservar")
            self.publicador.publicar(con, novel_id=novel_id, version=version)
            novel.fijar_estado_obra(con, novel_id=novel_id, estado=destino)
            repository.actualizar_trabajo(
                con,
                novel_id=novel_id,
                trabajo_id=t["id"],
                cambios={
                    "estado": destino,
                    "estado_cola": "terminado",
                    "version_resultante": version,
                    "terminada_en": ahora(),
                },
            )

        with self.r.trazador.span("publicar", metadata={"version": version}):
            await self.r.db.en_transaccion(publicar)

    async def _detener(
        self, t: dict[str, Any], motivo: str, detalle: str, *, devolver_al_editor: bool = False
    ) -> None:
        motor = PolicyEngine(self.r.config)

        def detener(con: sqlite3.Connection) -> None:
            actual = novel.estado_de_obra(con, novel_id=t["novel_id"])
            transiciones = []
            if devolver_al_editor:
                # El gate falló: la candidata queda rechazada y nunca será la vigente (TO-045).
                # El diagrama devuelve la novela al editor (Escribiendo); corregir la novela
                # entera exige retcon, así que se detiene ahí mismo (A-47, A-79, A-113).
                self.publicador.rechazar(con, novel_id=t["novel_id"], version=t["version_objetivo"])
                actual = aplicar("Novela", actual, "DevolverAlEditor")
                transiciones.append("DevolverAlEditor")
            destino = aplicar("Novela", actual, "Detener")
            transiciones.append("Detener")
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
                detalle={"detalle": detalle[:2000], "transiciones": transiciones},
            )

        await self.r.db.en_transaccion(detener)
