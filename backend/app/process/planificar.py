"""El planificador: del brief al esquema de la obra (RF-NOVEL-01).

El esquema fija el destino de cada capítulo de una vez. Se valida en dos niveles: el schema
—que la salida sea un `Esquema`— y el dominio —número de capítulos, destinatario, alcances
que nombran entidades del propio esquema, elementos obligatorios repartidos—. Los dos son
`schema_valido` (fila O-01). Un esquema que no vale se pide otra vez con el motivo, hasta el
límite de `orquestacion.max_intentos_capitulo` (D-23), y agotado detiene la novela.
"""

from __future__ import annotations

import json
import sqlite3

from pydantic import ValidationError

from app.commons.errores import LimiteDeIntentosAgotado, NovelaNoEncontrada
from app.commons.llm import SalidaInvalida
from app.commons.llm.esquema import esquema_de_salida
from app.commons.recursos import Recursos
from app.context import service as context
from app.guardrail import service as guardrail
from app.intake.service import BriefNovela, leer_brief
from app.novel import service as novel
from app.process import repository
from app.process.schemas import Esquema

ESQUEMA_SALIDA = esquema_de_salida(Esquema)


def errores_de_esquema(esquema: Esquema, brief: BriefNovela, total: int) -> list[str]:
    errores: list[str] = []
    capitulos = esquema.capitulos
    if len(capitulos) != total:
        errores.append(
            f"el esquema tiene {len(capitulos)} capítulos y la obra tiene {total} capítulos"
        )
    numeros = [c.numero for c in capitulos]
    if numeros != list(range(1, len(capitulos) + 1)):
        errores.append(f"los capítulos tienen que ir numerados de 1 en adelante: {numeros}")
    titulos = [c.titulo_provisional.strip() for c in capitulos]
    if any(not t for t in titulos) or len(set(titulos)) != len(titulos):
        errores.append("los títulos de capítulo tienen que ser únicos y no vacíos")

    nombres_personajes = [p.nombre for p in esquema.personajes]
    nombres_lugares = [lugar.nombre for lugar in esquema.lugares]
    nombres_hilos = {h.nombre for h in esquema.hilos}
    if len(set(nombres_personajes)) != len(nombres_personajes):
        errores.append("hay personajes repetidos")
    if len(set(nombres_lugares)) != len(nombres_lugares):
        errores.append("hay lugares repetidos")
    destinatarios = [p.nombre for p in esquema.personajes if p.es_destinatario]
    esperado = brief.destinatario.nombre
    if destinatarios != [esperado]:
        errores.append(
            f"tiene que haber un único personaje con es_destinatario true y llamarse "
            f"exactamente {esperado!r}; hay {destinatarios}"
        )
    existentes = {
        "personaje": set(nombres_personajes),
        "lugar": set(nombres_lugares),
        "hilo": nombres_hilos,
    }
    for c in capitulos:
        if c.pov not in existentes["personaje"]:
            errores.append(f"capítulo {c.numero}: el POV {c.pov!r} no está entre los personajes")
        if c.lugar not in existentes["lugar"]:
            errores.append(f"capítulo {c.numero}: el lugar {c.lugar!r} no está entre los lugares")
        for entidad in c.restriccion.alcance:
            if entidad.tipo in existentes and entidad.nombre not in existentes[entidad.tipo]:
                errores.append(
                    f"capítulo {c.numero}: el alcance nombra el {entidad.tipo} {entidad.nombre!r}, "
                    "que no está en el esquema"
                )
    asignados = {e for c in capitulos for e in c.elementos}
    for elemento in brief.elementos_personalizados:
        if elemento.obligatorio and elemento.enunciado not in asignados:
            errores.append(
                f"el elemento obligatorio «{elemento.enunciado}» no está asignado a ningún capítulo"
            )
    return errores


def _persistir(
    con: sqlite3.Connection, *, novel_id: str, version: int, esquema: Esquema, brief: BriefNovela
) -> None:
    novel.fijar_titulo(con, novel_id=novel_id, titulo=esquema.titulo, premisa=esquema.premisa)
    novel.registrar_reparto(
        con,
        novel_id=novel_id,
        personajes=[
            novel.Personaje(
                nombre=p.nombre,
                deseo=p.deseo,
                herida=p.herida,
                rol_narrativo=p.rol_narrativo,
                voz=p.voz,
                es_destinatario=p.es_destinatario,
                fecha_nacimiento=(
                    brief.destinatario.fecha_nacimiento.isoformat()
                    if p.es_destinatario and brief.destinatario.fecha_nacimiento
                    else None
                ),
            )
            for p in esquema.personajes
        ],
        lugares=[
            novel.Lugar(nombre=lu.nombre, geografia=lu.geografia, atmosfera=lu.atmosfera)
            for lu in esquema.lugares
        ],
        hilos=[
            novel.HiloTrama(nombre=h.nombre, pregunta_dramatica=h.pregunta_dramatica)
            for h in esquema.hilos
        ],
    )
    for c in esquema.capitulos:
        restriccion_id = repository.insertar_restriccion(
            con,
            novel_id=novel_id,
            numero=c.numero,
            tipo=c.restriccion.tipo,
            enunciado=c.restriccion.enunciado,
            alcance=json.dumps([a.model_dump() for a in c.restriccion.alcance], ensure_ascii=False),
        )
        context.registrar_brief_capitulo(
            con,
            novel_id=novel_id,
            numero=c.numero,
            restriccion_id=restriccion_id,
            titulo_provisional=c.titulo_provisional,
            funcion_dramatica=c.funcion_dramatica,
            pov=c.pov,
            lugar=c.lugar,
            estado_entrada=c.estado_entrada,
            elementos=c.elementos,
        )
        novel.crear_capitulo(con, novel_id=novel_id, numero=c.numero, version=version)


async def planificar(r: Recursos, *, novel_id: str, version: int) -> Esquema:
    config = r.config
    total = config.umbrales.obra.capitulos
    with r.trazador.span("consultar_story_bible", entrada={"novel_id": novel_id, "rol": "planner"}):

        def leer(con: sqlite3.Connection) -> tuple[BriefNovela | None, list[str]]:
            brief = leer_brief(con, novel_id=novel_id)
            palabras = [p.forma for p in guardrail.palabras_de_novela(con, novel_id=novel_id)]
            return brief, palabras

        brief, palabras = await r.db.ejecutar(leer)
    if brief is None:
        raise NovelaNoEncontrada(f"no existe la novela {novel_id}", novel_id=novel_id)

    cap = config.umbrales.capitulo
    piezas = {
        "invariante": context.piezas_invariante(brief),
        "estructural": [
            context.Pieza(
                etiqueta="Forma de la obra",
                texto=(
                    f"La obra tiene exactamente {total} capítulos, numerados de 1 a {total}, "
                    f"de {cap.longitud_min_palabras} a {cap.longitud_max_palabras} "
                    "palabras cada uno."
                ),
                prioridad=10,
            )
        ],
        "anticontexto": context.piezas_anticontexto(
            config, brief, palabras_novela=palabras, textos_recientes=[]
        ),
    }
    ensamblador = context.Ensamblador(config, context.ContadorProveedor(r.llamador))
    tarea = "Devuelve el esquema completo de la obra."
    limite = config.umbrales.orquestacion.max_intentos_capitulo
    errores: list[str] = []
    for intento in range(limite + 1):
        instruccion = tarea
        if errores:
            instruccion += "\n\nEl esquema anterior no valía, corrígelo:\n" + "\n".join(
                f"- {e}" for e in errores
            )
        ensamblado = await ensamblador.ensamblar(
            "planificador", piezas, tarea=instruccion, esquema_salida=ESQUEMA_SALIDA
        )
        try:
            respuesta = await r.llamador.llamar(ensamblado.peticion)
            esquema = Esquema.model_validate(respuesta.datos)
            errores = errores_de_esquema(esquema, brief, total)
        except (ValidationError, SalidaInvalida) as e:
            errores = [f"la salida no cumple el schema del esquema: {e}"]
        r.trazador.score(
            "schema_valido",
            0.0 if errores else 1.0,
            comentario="; ".join(errores)[:2000] if errores else f"planner, intento {intento}",
        )
        if not errores:
            valido = esquema

            def persistir(con: sqlite3.Connection, valido: Esquema = valido) -> None:
                _persistir(con, novel_id=novel_id, version=version, esquema=valido, brief=brief)

            await r.db.en_transaccion(persistir)
            return valido
    raise LimiteDeIntentosAgotado(
        "el planificador agotó sus intentos: " + "; ".join(errores),
        novel_id=novel_id,
        intentos_restantes=0,
    )
