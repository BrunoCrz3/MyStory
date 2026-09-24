"""Llamada al judge: ensambla su contexto, pide la rúbrica y deja un score por criterio
(RF-QUA-04, RF-OBS-03). El contrato de la salida y su evaluación son de `quality/`."""

from __future__ import annotations

import sqlite3
from functools import partial

from app.commons.errores import NovelaNoEncontrada
from app.commons.llm import SalidaInvalida, SalidaTruncada
from app.commons.llm.esquema import esquema_de_salida
from app.commons.recursos import Recursos
from app.context import service as context
from app.intake.service import BriefNovela, leer_brief
from app.quality import service as quality

ESQUEMA_JUDGE = esquema_de_salida(quality.SalidaJudge)


async def juzgar(
    r: Recursos, *, novel_id: str, version: int, numero: int, titulo: str, texto: str
) -> quality.ResultadoJudge:
    def leer(con: sqlite3.Connection) -> tuple[BriefNovela, context.BriefCapitulo]:
        brief = leer_brief(con, novel_id=novel_id)
        bc = context.brief_de_capitulo(con, novel_id=novel_id, numero=numero)
        if brief is None or bc is None:
            raise NovelaNoEncontrada(
                f"la novela {novel_id} no tiene el capítulo {numero} planificado",
                novel_id=novel_id,
                capitulo=numero,
            )
        return brief, bc

    with r.trazador.span("consultar_story_bible", entrada={"capitulo": numero, "rol": "judge"}):
        brief, bc = await r.db.ejecutar(leer)
        piezas = await r.db.ejecutar(
            partial(
                context.piezas_judge,
                config=r.config,
                novel_id=novel_id,
                version=version,
                numero=numero,
                brief=brief,
                brief_capitulo=bc,
                titulo=titulo,
                texto=texto,
            )
        )
    ensamblador = context.Ensamblador(r.config, context.ContadorProveedor(r.llamador))
    ensamblado = await ensamblador.ensamblar(
        "judge",
        piezas,
        tarea=f"Puntúa el capítulo {numero} contra la rúbrica, criterio a criterio.",
        esquema_salida=ESQUEMA_JUDGE,
    )
    datos, error = None, None
    try:
        respuesta = await r.llamador.llamar(ensamblado.peticion)
        datos = respuesta.datos
    except (SalidaInvalida, SalidaTruncada) as e:
        error = str(e)
    d = brief.destinatario
    contexto = quality.ContextoJudge(
        destinatario=d.nombre,
        # Lo que el comprador contó: el brief y su texto libre, que se guardó ya saneado.
        soporte=[
            *d.rasgos,
            *d.recuerdos,
            *(e.enunciado for e in brief.elementos_personalizados),
            *(t.contenido for t in brief.textos_libres),
            *([brief.premisa] if brief.premisa else []),
            brief.dedicatoria.texto,
        ],
        temas_excluidos=brief.temas_excluidos,
        texto=texto,
    )
    resultado = quality.evaluar_judge(r.config, datos, error, contexto)
    for v in resultado.todos:
        # La justificación del judge es el comentario del score (RF-OBS-03).
        r.trazador.score(v.nombre, v.valor, comentario=v.detalle[:2000])
    return resultado
