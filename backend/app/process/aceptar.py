"""Aceptar un capítulo: extraer lo que introdujo y consolidarlo, en una sola transacción
(RF-PROC-10, RF-CANON-01, D-07).

Es **el único punto** donde la story bible cambia. La extracción corre después de que el
policy engine haya aceptado el capítulo, nunca antes; y la consolidación reparte la escritura
entre las features dueñas dentro de la transacción que abre `process/`: texto y estado del
capítulo, hechos con la decisión del policy engine, usos, promesas, snapshot, resumen, eventos
y elementos aparecidos. O entra todo, o nada.
"""

from __future__ import annotations

import sqlite3
from functools import partial

from pydantic import ValidationError

from app.canon import service as canon
from app.commons.errores import LimiteDeIntentosAgotado, NovelaNoEncontrada
from app.commons.llm import SalidaInvalida, SalidaTruncada
from app.commons.llm.esquema import esquema_de_salida
from app.commons.recursos import Recursos
from app.commons.tiempo import ahora
from app.context import service as context
from app.intake import service as intake
from app.novel import service as novel
from app.policy.service import PolicyEngine
from app.process import repository
from app.process.capitulo import ResultadoCapitulo
from app.process.schemas import Extraccion
from app.process.transiciones import aplicar

ESQUEMA_EXTRACCION = esquema_de_salida(Extraccion)


class _Conocido:
    """Lo que el extractor ya sabe de la novela, con los alias que puede citar."""

    def __init__(self, hechos: list[canon.Hecho], promesas: list[canon.Promesa]) -> None:
        self.hechos = {f"H{i}": h for i, h in enumerate(hechos, 1)}
        self.promesas = {f"P{i}": p for i, p in enumerate(promesas, 1)}


def _leer(
    con: sqlite3.Connection, *, novel_id: str, version: int, numero: int
) -> tuple[novel.CapituloEnCurso, context.BriefCapitulo, _Conocido, list[str], list[str]]:
    cap = novel.capitulo_en_curso(con, novel_id=novel_id, numero=numero, version=version)
    bc = context.brief_de_capitulo(con, novel_id=novel_id, numero=numero)
    if cap is None or bc is None:
        raise NovelaNoEncontrada(f"no hay capítulo {numero} en {novel_id}", novel_id=novel_id)
    anteriores = [
        c.capitulo_id
        for c in novel.capitulos_aceptados(con, novel_id=novel_id, version=version)
        if c.numero < numero
    ]
    conocido = _Conocido(
        canon.hechos_vigentes(con, novel_id=novel_id, version=version),
        [
            p
            for p in canon.promesas_de(
                con, novel_id=novel_id, version=version, capitulo_ids=anteriores
            )
            if p.estado == "pendiente"
        ],
    )
    elementos = [e for _, e, _ in intake.elementos_personalizados(con, novel_id=novel_id)]
    nombres = novel.nombres_de_la_obra(con, novel_id=novel_id)
    return cap, bc, conocido, elementos, nombres


async def _extraer(
    r: Recursos,
    *,
    capitulo_id: str,
    texto: str,
    conocido: _Conocido,
    elementos: list[str],
    nombres: list[str],
    novel_id: str,
) -> Extraccion:
    piezas = {
        "estructural": [
            context.Pieza(
                etiqueta="Hechos ya conocidos (cítalos por su alias)",
                texto="\n".join(f"{a}: {h.enunciado}" for a, h in conocido.hechos.items())
                or "(ninguno)",
                prioridad=10,
            ),
            context.Pieza(
                etiqueta="Promesas abiertas (cítalas por su alias si este capítulo las paga)",
                texto="\n".join(f"{a}: {p.enunciado}" for a, p in conocido.promesas.items())
                or "(ninguna)",
                prioridad=10,
            ),
            context.Pieza(
                etiqueta="Elementos personalizados del encargo (cita el enunciado exacto)",
                texto="\n".join(f"- {e}" for e in elementos) or "(ninguno)",
                prioridad=10,
            ),
            context.Pieza(
                etiqueta="Personajes y lugares de la story bible",
                texto=", ".join(nombres),
                prioridad=10,
            ),
        ],
        "local": [context.Pieza(etiqueta="Capítulo aceptado", texto=texto, prioridad=10)],
    }
    ensamblador = context.Ensamblador(r.config, context.ContadorProveedor(r.llamador))
    limite = r.config.umbrales.orquestacion.max_intentos_capitulo
    motivo = ""
    for intento in range(limite + 1):
        tarea = "Extrae lo que este capítulo ha establecido y lo que ha usado."
        if motivo:
            tarea += f"\n\nLa extracción anterior no valía: {motivo}"
        ensamblado = await ensamblador.ensamblar(
            "extractor", piezas, tarea=tarea, esquema_salida=ESQUEMA_EXTRACCION
        )
        try:
            respuesta = await r.llamador.llamar(ensamblado.peticion)
            await r.db.ejecutar(
                partial(
                    novel.sumar_consumo,
                    novel_id=novel_id,
                    capitulo_id=capitulo_id,
                    tokens_entrada=respuesta.tokens_entrada,
                    tokens_salida=respuesta.tokens_salida,
                    coste_usd=respuesta.coste_usd,
                )
            )
            extraccion = Extraccion.model_validate(respuesta.datos)
        except (ValidationError, SalidaInvalida, SalidaTruncada) as e:
            motivo = f"no cumple su schema ({type(e).__name__})"
            r.trazador.score(
                "schema_valido", 0.0, comentario=f"extractor, intento {intento}: {motivo}"
            )
            continue
        r.trazador.score("schema_valido", 1.0, comentario=f"extractor, intento {intento}")
        return extraccion
    raise LimiteDeIntentosAgotado(f"el extractor agotó sus intentos: {motivo}", novel_id=novel_id)


def _consolidar(
    con: sqlite3.Connection,
    *,
    motor: PolicyEngine,
    novel_id: str,
    version: int,
    numero: int,
    capitulo: novel.CapituloEnCurso,
    brief_capitulo: context.BriefCapitulo,
    titulo: str,
    texto: str,
    extraccion: Extraccion,
    conocido: _Conocido,
    generacion_id: str | None,
) -> canon.ResultadoConsolidacion:
    destino = aplicar("Capitulo", capitulo.estado, "Aceptar")
    novel.guardar_texto_aceptado(
        con,
        novel_id=novel_id,
        capitulo_id=capitulo.capitulo_id,
        titulo=titulo,
        texto=texto,
        gancho_cierre=extraccion.gancho_cierre,
        pov=brief_capitulo.pov,
        lugar=brief_capitulo.lugar,
    )
    novel.fijar_estado_capitulo(
        con,
        novel_id=novel_id,
        capitulo_id=capitulo.capitulo_id,
        estado=destino,
        intentos=capitulo.intentos,
    )
    vigentes = [h.enunciado for h in canon.hechos_vigentes(con, novel_id=novel_id, version=version)]

    def decidir(hecho: canon.HechoPropuesto) -> bool:
        adoptado = motor.decidir_hecho(
            con, novel_id=novel_id, texto=texto, hecho=hecho, conocidos=vigentes
        )
        if adoptado:
            vigentes.append(hecho.enunciado)
        return adoptado

    momento_base = numero * 100
    resultado = canon.consolidar(
        con,
        novel_id=novel_id,
        version=version,
        texto=texto,
        entrada=canon.Consolidacion(
            capitulo_id=capitulo.capitulo_id,
            numero=numero,
            hechos_nuevos=[
                canon.HechoNuevo(
                    enunciado=h.enunciado, tipo=h.tipo, fragmento_soporte=h.fragmento_soporte
                )
                for h in extraccion.hechos_nuevos
            ],
            hechos_usados=[
                conocido.hechos[a].hecho_id
                for a in extraccion.hechos_usados
                if a in conocido.hechos
            ],
            promesas_abiertas=[
                canon.PromesaNueva(enunciado=p.enunciado, tipo=p.tipo)
                for p in extraccion.promesas_abiertas
            ],
            promesas_pagadas=[
                conocido.promesas[a].promesa_id
                for a in extraccion.promesas_pagadas
                if a in conocido.promesas
            ],
            personajes_presentes=extraccion.personajes_presentes,
            ubicaciones={u.personaje: u.lugar for u in extraccion.ubicaciones},
            momento=momento_base,
        ),
        decidir=decidir,
    )
    context.guardar_resumen(
        con, novel_id=novel_id, capitulo_id=capitulo.capitulo_id, texto=extraccion.resumen
    )
    novel.registrar_eventos(
        con,
        novel_id=novel_id,
        capitulo_id=capitulo.capitulo_id,
        eventos=[
            novel.EventoNarrado(
                descripcion=e.descripcion,
                momento=momento_base + e.orden,
                lugar=e.lugar,
                personajes=e.personajes,
            )
            for e in extraccion.eventos
        ],
    )
    novel.registrar_elementos_en_capitulo(
        con,
        novel_id=novel_id,
        capitulo_id=capitulo.capitulo_id,
        enunciados=extraccion.elementos_presentes,
    )
    if generacion_id is not None:
        # El checkpoint entra en la misma transacción: aceptado y checkpoint van juntos.
        repository.guardar_checkpoint(
            con, novel_id=novel_id, trabajo_id=generacion_id, ultimo=numero, ahora=ahora()
        )
    return resultado


async def aceptar(
    r: Recursos,
    *,
    novel_id: str,
    version: int,
    numero: int,
    resultado: ResultadoCapitulo,
    generacion_id: str | None = None,
) -> canon.ResultadoConsolidacion:
    if resultado.accion != "aceptar" or resultado.borrador is None:
        raise ValueError("solo se acepta un capítulo que el policy engine ha aceptado")
    borrador = resultado.borrador
    capitulo, bc, conocido, elementos, nombres = await r.db.ejecutar(
        partial(_leer, novel_id=novel_id, version=version, numero=numero)
    )
    # Comprueba la transición antes de pagar la extracción: aceptar dos veces es un error.
    aplicar("Capitulo", capitulo.estado, "Aceptar")
    extraccion = await _extraer(
        r,
        capitulo_id=capitulo.capitulo_id,
        texto=borrador.texto,
        conocido=conocido,
        elementos=elementos,
        nombres=nombres,
        novel_id=novel_id,
    )
    motor = PolicyEngine(r.config)
    with r.trazador.span("consolidar", metadata={"numero": numero, "version": version}):
        return await r.db.en_transaccion(
            partial(
                _consolidar,
                motor=motor,
                novel_id=novel_id,
                version=version,
                numero=numero,
                capitulo=capitulo,
                brief_capitulo=bc,
                titulo=borrador.titulo,
                texto=borrador.texto,
                extraccion=extraccion,
                conocido=conocido,
                generacion_id=generacion_id,
            )
        )
