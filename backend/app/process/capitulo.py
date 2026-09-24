"""Ciclo de un capítulo: escribir, hook de policy, hook de capítulo, decisión y reescritura
(`architecture.md` § Hooks y policy engine).

Cada cambio de estado del capítulo pasa por la tabla de transiciones (`aplicar`), y el orden
de validación es fijo: lo barato y determinista primero. Si el hook de policy falla, el de
capítulo no corre: no tiene sentido medir la prosa de un capítulo que no cumple su schema.

El borrador vive en memoria hasta que se acepta: uno rechazado no deja rastro en la story
bible (RF-CANON-01). Lo que sí queda es la decisión en el audit log y el score en la traza.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from functools import partial
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.canon import service as canon
from app.commons.errores import NovelaNoEncontrada
from app.commons.llm import SalidaInvalida, SalidaTruncada
from app.commons.llm.esquema import esquema_de_salida
from app.commons.recursos import Recursos
from app.context import service as context
from app.guardrail import service as guardrail
from app.intake.service import BriefNovela, leer_brief
from app.novel import service as novel
from app.policy.service import DecisionCapitulo, PolicyEngine, Veredicto
from app.process import hooks
from app.process.editor import corregir
from app.process.judge import juzgar
from app.process.schemas import BorradorCapitulo
from app.process.transiciones import aplicar
from app.quality import service as quality

ESQUEMA_BORRADOR = esquema_de_salida(BorradorCapitulo)


class ResultadoCapitulo(BaseModel):
    model_config = ConfigDict(frozen=True)

    accion: str
    capitulo_id: str
    intentos: int
    borrador: BorradorCapitulo | None = None
    detenida_por: str | None = None


@dataclass
class _Datos:
    brief: BriefNovela
    brief_capitulo: context.BriefCapitulo
    palabras: list[str]
    nombres: list[str]
    hechos: list[str]
    previstas: list[quality.EntidadPrevista]
    anteriores: list[str]
    personajes: list[str]


def _previstas(
    con: sqlite3.Connection, *, novel_id: str, numero: int, total: int, ya_nombrados: str
) -> list[quality.EntidadPrevista]:
    """Personajes y lugares cuya primera aparición en el plan es posterior a este capítulo y
    que el canon todavía no ha nombrado (O-42)."""
    primera: dict[str, int] = {}
    for n in range(1, total + 1):
        bc = context.brief_de_capitulo(con, novel_id=novel_id, numero=n)
        if bc is None:
            break
        for nombre in (bc.pov, bc.lugar, *bc.entidades):
            primera.setdefault(nombre, n)
    return [
        quality.EntidadPrevista(nombre=nombre, capitulo=n)
        for nombre, n in primera.items()
        if n > numero and nombre not in ya_nombrados
    ]


async def mover(
    r: Recursos,
    *,
    novel_id: str,
    capitulo: novel.CapituloEnCurso,
    accion: str,
    sumar_intento: bool = False,
) -> novel.CapituloEnCurso:
    """Aplica una acción de la máquina del capítulo y la persiste."""
    destino = aplicar("Capitulo", capitulo.estado, accion)
    intentos = capitulo.intentos + (1 if sumar_intento else 0)
    await r.db.ejecutar(
        lambda con: novel.fijar_estado_capitulo(
            con,
            novel_id=novel_id,
            capitulo_id=capitulo.capitulo_id,
            estado=destino,
            intentos=intentos,
        )
    )
    return capitulo.model_copy(update={"estado": destino, "intentos": intentos})


async def _leer(
    r: Recursos, *, novel_id: str, version: int, numero: int
) -> tuple[_Datos, novel.CapituloEnCurso]:
    def leer(con: sqlite3.Connection) -> tuple[_Datos, novel.CapituloEnCurso]:
        brief = leer_brief(con, novel_id=novel_id)
        bc = context.brief_de_capitulo(con, novel_id=novel_id, numero=numero)
        cap = novel.capitulo_en_curso(con, novel_id=novel_id, numero=numero, version=version)
        if brief is None or bc is None or cap is None:
            raise NovelaNoEncontrada(
                f"la novela {novel_id} no tiene el capítulo {numero} planificado "
                f"en la versión {version}",
                novel_id=novel_id,
                capitulo=numero,
            )
        destinatario = brief.destinatario
        hechos = [
            h.enunciado
            for h in canon.hechos_vigentes(
                con, novel_id=novel_id, version=version, hasta_numero=numero - 1
            )
        ]
        # La edad del brief es canon desde el principio, aunque ningún capítulo la cuente.
        hechos.append(f"{destinatario.nombre} tiene {destinatario.edad} años.")
        datos = _Datos(
            brief=brief,
            brief_capitulo=bc,
            palabras=[p.forma for p in guardrail.palabras_de_novela(con, novel_id=novel_id)],
            nombres=novel.nombres_de_la_obra(con, novel_id=novel_id),
            hechos=hechos,
            previstas=_previstas(
                con,
                novel_id=novel_id,
                numero=numero,
                total=r.config.umbrales.obra.capitulos,
                ya_nombrados=" ".join(hechos),
            ),
            anteriores=[
                c.texto
                for c in novel.capitulos_aceptados(con, novel_id=novel_id, version=version)
                if c.numero < numero
            ],
            personajes=[p.nombre for p in novel.personajes(con, novel_id=novel_id)],
        )
        return datos, cap

    return await r.db.ejecutar(leer)


def _decidir_y_registrar(
    con: sqlite3.Connection,
    *,
    motor: PolicyEngine,
    novel_id: str,
    capitulo_id: str,
    intentos: int,
    resultados: list[quality.ResultadoValidador],
    reescrituras_por_guardrail: int,
) -> DecisionCapitulo:
    """La decisión del policy engine y el informe de crítica del intento, en una transacción."""
    decision = motor.decidir_capitulo(
        con,
        novel_id=novel_id,
        capitulo_id=capitulo_id,
        intentos=intentos,
        veredictos=[
            Veredicto(nombre=v.nombre, pasa=v.pasa, cierra_el_paso=v.cierra_el_paso, valor=v.valor)
            for v in resultados
        ],
        reescrituras_por_guardrail=reescrituras_por_guardrail,
    )
    quality.registrar_informe(
        con,
        novel_id=novel_id,
        capitulo_id=capitulo_id,
        intento=intentos,
        decision=decision.accion,
        resultados=resultados,
    )
    return decision


def _tarea(r: Recursos, numero: int, informe: list[str], aviso: str | None = None) -> str:
    cap = r.config.umbrales.capitulo
    tarea = (
        f"Escribe el capítulo {numero} completo, de {cap.longitud_min_palabras} a "
        f"{cap.longitud_max_palabras} palabras, y devuelve su título y su texto."
    )
    if aviso:
        tarea += "\n\n" + aviso
    if informe:
        tarea += (
            "\n\nEl borrador anterior no pasó la validación. Escríbelo de nuevo corrigiendo:\n"
            + "\n".join(f"- {d}" for d in informe)
        )
    return tarea


async def ciclo_capitulo(
    r: Recursos, *, novel_id: str, version: int, numero: int, aviso: str | None = None
) -> ResultadoCapitulo:
    """Escribe y valida el capítulo `numero` de `version`. `aviso` es lo que el redactor tiene
    que saber además de su contexto: en una regeneración dirigida, qué hecho cambió."""
    config = r.config
    motor = PolicyEngine(config)
    ensamblador = context.Ensamblador(config, context.ContadorProveedor(r.llamador))
    with r.trazador.span(
        "consultar_story_bible", entrada={"novel_id": novel_id, "capitulo": numero}
    ):
        datos, capitulo = await _leer(r, novel_id=novel_id, version=version, numero=numero)
    perfil = guardrail.PerfilLector(
        edad=datos.brief.destinatario.edad, ocasion=datos.brief.ocasion.tipo
    )
    piezas_de = partial(
        context.piezas_redactor,
        config=config,
        novel_id=novel_id,
        version=version,
        numero=numero,
        brief=datos.brief,
        brief_capitulo=datos.brief_capitulo,
        palabras_novela=datos.palabras,
    )
    informe: list[str] = []
    reescrituras_por_guardrail = 0

    async def validar(
        salida: dict[str, Any] | None, error: str | None, cid: str, intento: int
    ) -> tuple[list[quality.ResultadoValidador], BorradorCapitulo | None]:
        """Hook de policy, hook de capítulo y judge, en ese orden, con un score por validador.

        Si el hook de policy falla, nada más corre —no se paga un juicio sobre un borrador que
        no cumple su schema o lleva una palabra vetada— y no se devuelve borrador.
        """
        nonlocal reescrituras_por_guardrail
        with r.trazador.span("hook_policy"):
            v_schema, borrador = hooks.schema_valido(salida, error)
            resultados = [v_schema]
            if borrador is not None:
                v_palabras, coincidencias = hooks.palabras_prohibidas(
                    config, borrador, palabras_novela=datos.palabras, perfil=perfil
                )
                resultados.append(v_palabras)
                if coincidencias:
                    reescrituras_por_guardrail += 1
                    await r.db.en_transaccion(
                        partial(
                            motor.registrar_coincidencias,
                            novel_id=novel_id,
                            capitulo_id=cid,
                            intento=intento,
                            coincidencias=coincidencias,
                        )
                    )
                else:
                    reescrituras_por_guardrail = 0
        if borrador is None or not all(v.pasa for v in resultados):
            for v in resultados:
                r.trazador.score(v.nombre, v.valor, comentario=v.detalle[:2000])
            # Sin borrador que corregir: el editor no se llama y la decisión es del policy.
            return resultados, None
        with r.trazador.span("hook_capitulo"):
            voz = datos.brief.voz_narrativa
            resultados += await quality.hook_capitulo(
                config,
                quality.EntradaHookCapitulo(
                    titulo=borrador.titulo,
                    texto=borrador.texto,
                    nombres=datos.nombres,
                    hechos=datos.hechos,
                    reglas_mundo=datos.brief.reglas_mundo,
                    alcance=datos.brief_capitulo.alcance,
                    previstas=datos.previstas,
                    anteriores=datos.anteriores,
                    persona=voz.persona,
                    tiempo_verbal=voz.tiempo_verbal,
                    focalizacion=voz.focalizacion,
                    pov=datos.brief_capitulo.pov,
                    personajes=datos.personajes,
                ),
            )
        for v in resultados:
            r.trazador.score(v.nombre, v.valor, comentario=v.detalle[:2000])
        # El judge deja sus propios scores, con la justificación de cada criterio.
        juicio = await juzgar(
            r,
            novel_id=novel_id,
            version=version,
            numero=numero,
            titulo=borrador.titulo,
            texto=borrador.texto,
        )
        return [*resultados, *juicio.todos], borrador

    with r.trazador.span("capitulo", metadata={"numero": numero, "version": version}):
        while True:
            accion = "Escribir" if capitulo.estado == "Pendiente" else "Reintentar"
            capitulo = await mover(r, novel_id=novel_id, capitulo=capitulo, accion=accion)
            cid = capitulo.capitulo_id

            with r.trazador.span("consultar_story_bible", entrada={"capitulo": numero}):
                piezas = await r.db.ejecutar(piezas_de)
            ensamblado = await ensamblador.ensamblar(
                "redactor",
                piezas,
                tarea=_tarea(r, numero, informe, aviso),
                esquema_salida=ESQUEMA_BORRADOR,
            )
            salida, error = None, None
            try:
                respuesta = await r.llamador.llamar(ensamblado.peticion)
                salida = respuesta.datos
                await r.db.ejecutar(
                    partial(
                        novel.sumar_consumo,
                        novel_id=novel_id,
                        capitulo_id=cid,
                        tokens_entrada=respuesta.tokens_entrada,
                        tokens_salida=respuesta.tokens_salida,
                        coste_usd=respuesta.coste_usd,
                    )
                )
            except (SalidaInvalida, SalidaTruncada) as e:
                error = str(e)
            capitulo = await mover(r, novel_id=novel_id, capitulo=capitulo, accion="Validar")

            resultados, borrador = await validar(salida, error, cid, capitulo.intentos)
            if borrador is not None and quality.defectos_que_cierran(resultados):
                # El editor corrige lo que cierra el paso, y su versión vuelve a pasar todo.
                correccion = await corregir(
                    r,
                    novel_id=novel_id,
                    version=version,
                    numero=numero,
                    titulo=borrador.titulo,
                    texto=borrador.texto,
                    informe=quality.informe_para_editor(resultados),
                )
                for defecto in correccion.sistemicos:
                    await r.db.en_transaccion(
                        partial(
                            motor.registrar_defecto_sistemico,
                            novel_id=novel_id,
                            capitulo_id=cid,
                            intento=capitulo.intentos,
                            defecto=defecto,
                        )
                    )
                resultados, borrador = await validar(
                    correccion.datos, correccion.error, cid, capitulo.intentos
                )

            decision = await r.db.en_transaccion(
                partial(
                    _decidir_y_registrar,
                    motor=motor,
                    novel_id=novel_id,
                    capitulo_id=cid,
                    intentos=capitulo.intentos,
                    resultados=resultados,
                    reescrituras_por_guardrail=reescrituras_por_guardrail,
                )
            )
            if decision.accion == "aceptar":
                return ResultadoCapitulo(
                    accion="aceptar", capitulo_id=cid, intentos=capitulo.intentos, borrador=borrador
                )
            if decision.accion == "devolver":
                capitulo = await mover(
                    r, novel_id=novel_id, capitulo=capitulo, accion="Reescribir", sumar_intento=True
                )
                informe = [d.descripcion for v in resultados for d in v.defectos] or [
                    v.detalle for v in resultados if not v.pasa
                ]
                continue
            # Agotado: el contador cuenta las reescrituras hechas, y esta ya no se hace.
            capitulo = await mover(r, novel_id=novel_id, capitulo=capitulo, accion="Reescribir")
            capitulo = await mover(r, novel_id=novel_id, capitulo=capitulo, accion="Agotar")
            return ResultadoCapitulo(
                accion=decision.accion,
                capitulo_id=cid,
                intentos=capitulo.intentos,
                detenida_por=decision.detenida_por,
            )
