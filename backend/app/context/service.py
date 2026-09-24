"""Servicio de contexto: qué ve cada rol, capa por capa (RF-CTX-01).

Lo que aquí se construye son **piezas**; el `Ensamblador` las cuenta, las comprime si hace
falta y arma la petición. Toda lectura de la story bible para un rol va dentro del span
`consultar_story_bible`, que es la tool de lectura de `architecture.md` § Agentes.
"""

from __future__ import annotations

import json
import sqlite3
import uuid

from pydantic import BaseModel, ConfigDict

from app.canon import service as canon
from app.commons.config import Config
from app.context import repository
from app.context.ensamblador import Contador, Ensamblado, Ensamblador, Pieza
from app.context.fuentes import ContadorProveedor, expresiones_repetidas, recuperar_fragmentos
from app.guardrail import service as guardrail
from app.intake.service import BriefNovela
from app.novel import service as novel

__all__ = [
    "BriefCapitulo",
    "Contador",
    "ContadorProveedor",
    "Ensamblado",
    "Ensamblador",
    "Pieza",
    "brief_de_capitulo",
    "expresiones_repetidas",
    "guardar_resumen",
    "piezas_anticontexto",
    "piezas_invariante",
    "piezas_redactor",
    "recuperar_fragmentos",
    "registrar_brief_capitulo",
    "resumen_de",
]


class BriefCapitulo(BaseModel):
    """Encargo de un capítulo: estado de entrada más restricción de destino."""

    model_config = ConfigDict(frozen=True)

    numero: int
    titulo_provisional: str
    funcion_dramatica: str
    pov: str
    lugar: str
    estado_entrada: str
    restriccion_tipo: str
    restriccion_enunciado: str
    alcance: list[dict[str, str]]
    elementos: list[str]

    @property
    def entidades(self) -> list[str]:
        return [a["nombre"] for a in self.alcance if a["tipo"] in ("personaje", "lugar")]


def piezas_invariante(brief: BriefNovela) -> list[Pieza]:
    """Lo que no cambia entre capítulos: premisa, brief, dedicatoria, voz narrativa."""
    d = brief.destinatario
    piezas = [
        Pieza(
            etiqueta="Encargo",
            texto=(
                f"Género: {brief.genero}. Tono: {brief.tono}."
                + (f"\nPremisa: {brief.premisa}" if brief.premisa else "")
            ),
            prioridad=10,
        ),
        Pieza(
            etiqueta="Destinatario",
            texto="\n".join(
                [
                    f"Nombre: {d.nombre}",
                    f"Edad: {d.edad}",
                    *(f"Rasgo: {r}" for r in d.rasgos),
                    *(f"Recuerdo: {r}" for r in d.recuerdos),
                ]
            ),
            prioridad=10,
        ),
        Pieza(
            etiqueta="Ocasión",
            texto=f"{brief.ocasion.tipo}"
            + (
                f", tono esperado: {brief.ocasion.tono_esperado}"
                if brief.ocasion.tono_esperado
                else ""
            ),
            prioridad=9,
        ),
        Pieza(etiqueta="Dedicatoria", texto=brief.dedicatoria.texto, prioridad=8),
        Pieza(
            etiqueta="Voz narrativa",
            texto=(
                f"Persona {brief.voz_narrativa.persona}, "
                f"tiempo {brief.voz_narrativa.tiempo_verbal}, "
                f"focalización {brief.voz_narrativa.focalizacion}."
            ),
            prioridad=10,
        ),
    ]
    if brief.elementos_personalizados:
        piezas.append(
            Pieza(
                etiqueta="Elementos personalizados",
                texto="\n".join(
                    f"- {'[obligatorio]' if e.obligatorio else '[opcional]'} {e.enunciado}"
                    for e in brief.elementos_personalizados
                ),
                prioridad=10,
            )
        )
    if brief.reglas_mundo:
        piezas.append(
            Pieza(
                etiqueta="Reglas del mundo",
                texto="\n".join(f"- {r}" for r in brief.reglas_mundo),
                prioridad=10,
            )
        )
    for texto in brief.textos_libres:
        piezas.append(
            Pieza(
                etiqueta=f"Texto libre del comprador ({texto.procedencia or 'sin procedencia'})",
                texto=texto.contenido,
                no_confiable=True,
                prioridad=7,
            )
        )
    return piezas


def piezas_anticontexto(
    config: Config,
    brief: BriefNovela,
    *,
    palabras_novela: list[str],
    textos_recientes: list[str],
) -> list[Pieza]:
    """Palabras prohibidas de los tres niveles, temas excluidos y expresiones ya usadas."""
    perfil = guardrail.PerfilLector(edad=brief.destinatario.edad, ocasion=brief.ocasion.tipo)
    vetadas = [
        p.forma
        for p in guardrail.Guardrail(config).palabras(
            palabras_novela=palabras_novela, perfil=perfil
        )
    ]
    piezas = [
        Pieza(
            etiqueta="Palabras prohibidas (en ninguna forma)",
            texto=", ".join(sorted(set(vetadas))),
            prioridad=10,
        )
    ]
    if brief.temas_excluidos:
        piezas.append(
            Pieza(
                etiqueta="Temas excluidos (ni siquiera sin nombrarlos)",
                texto="\n".join(f"- {t}" for t in brief.temas_excluidos),
                prioridad=10,
            )
        )
    repetidas = expresiones_repetidas(textos_recientes, config)
    if repetidas:
        piezas.append(
            Pieza(
                etiqueta="Expresiones ya usadas: no las repitas",
                texto="\n".join(f"- {r}" for r in repetidas),
                prioridad=1,
            )
        )
    return piezas


def registrar_brief_capitulo(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    numero: int,
    restriccion_id: str,
    titulo_provisional: str,
    funcion_dramatica: str,
    pov: str,
    lugar: str,
    estado_entrada: str,
    elementos: list[str],
) -> str:
    return repository.insertar_brief_capitulo(
        con,
        novel_id=novel_id,
        brief_id=str(uuid.uuid4()),
        numero=numero,
        restriccion_id=restriccion_id,
        titulo_provisional=titulo_provisional,
        funcion_dramatica=funcion_dramatica,
        pov=pov,
        lugar=lugar,
        estado_entrada=estado_entrada,
        elementos=json.dumps(elementos, ensure_ascii=False),
    )


def brief_de_capitulo(
    con: sqlite3.Connection, *, novel_id: str, numero: int
) -> BriefCapitulo | None:
    fila = repository.leer_brief_capitulo(con, novel_id=novel_id, numero=numero)
    if fila is None:
        return None
    return BriefCapitulo(
        numero=fila["numero"],
        titulo_provisional=fila["titulo_provisional"],
        funcion_dramatica=fila["funcion_dramatica"],
        pov=fila["pov"],
        lugar=fila["lugar"],
        estado_entrada=fila["estado_entrada"],
        restriccion_tipo=fila["tipo"],
        restriccion_enunciado=fila["enunciado"],
        alcance=json.loads(fila["alcance"]),
        elementos=json.loads(fila["elementos"]),
    )


def guardar_resumen(
    con: sqlite3.Connection, *, novel_id: str, capitulo_id: str, texto: str
) -> None:
    """El `Resumen de capítulo` se escribe al consolidar, en su misma transacción."""
    repository.insertar_resumen(con, novel_id=novel_id, capitulo_id=capitulo_id, texto=texto)


def resumen_de(con: sqlite3.Connection, *, novel_id: str, capitulo_id: str) -> str | None:
    return repository.leer_resumen(con, novel_id=novel_id, capitulo_id=capitulo_id)


def _render_snapshot(snapshot: canon.Snapshot) -> str:
    lineas = [f"Al cierre del capítulo {snapshot.numero}:"]
    if snapshot.personajes_presentes:
        lineas.append("Presentes: " + ", ".join(snapshot.personajes_presentes))
    for quien, donde in snapshot.ubicaciones.items():
        lineas.append(f"{quien} está en {donde}")
    if snapshot.hechos:
        lineas.append("Es verdad en la novela:")
        lineas += [f"- {h}" for h in snapshot.hechos]
    if snapshot.promesas_pendientes:
        lineas.append("Promesas abiertas ante el lector:")
        lineas += [f"- {p}" for p in snapshot.promesas_pendientes]
    return "\n".join(lineas)


def piezas_redactor(
    con: sqlite3.Connection,
    config: Config,
    *,
    novel_id: str,
    version: int,
    numero: int,
    brief: BriefNovela,
    brief_capitulo: BriefCapitulo,
    palabras_novela: list[str],
) -> dict[str, list[Pieza]]:
    """Las siete capas del contexto del redactor para el capítulo `numero` (RF-CTX-01)."""
    cap = config.umbrales.capitulo
    anteriores = [
        c
        for c in novel.capitulos_aceptados(con, novel_id=novel_id, version=version)
        if c.numero < numero
    ]
    bc = brief_capitulo
    estructural = [
        Pieza(
            etiqueta=f"Brief del capítulo {numero}",
            texto="\n".join(
                [
                    f"Título provisional: {bc.titulo_provisional}",
                    f"Función dramática: {bc.funcion_dramatica}",
                    f"Punto de vista: {bc.pov}",
                    f"Lugar: {bc.lugar}",
                    f"Longitud: de {cap.longitud_min_palabras} "
                    f"a {cap.longitud_max_palabras} palabras",
                ]
            ),
            prioridad=10,
        ),
        Pieza(
            etiqueta="Restricción de destino (se cumple al terminar el capítulo)",
            texto=f"[{bc.restriccion_tipo}] {bc.restriccion_enunciado}",
            prioridad=10,
        ),
    ]
    if bc.elementos:
        estructural.append(
            Pieza(
                etiqueta="Elementos personalizados que este capítulo integra",
                texto="\n".join(f"- {e}" for e in bc.elementos),
                prioridad=10,
            )
        )

    estado = [Pieza(etiqueta="Estado de entrada", texto=bc.estado_entrada, prioridad=10)]
    if anteriores:
        previo = anteriores[-1]
        snapshot = canon.snapshot_de(
            con, novel_id=novel_id, version=version, capitulo_id=previo.capitulo_id
        )
        if snapshot is not None:
            estado.append(Pieza(texto=_render_snapshot(snapshot), prioridad=9))

    local = [
        Pieza(
            etiqueta=f"Capítulo {c.numero}: {c.titulo or ''}",
            texto=c.texto,
            resumen=resumen_de(con, novel_id=novel_id, capitulo_id=c.capitulo_id),
            prioridad=c.numero,
        )
        for c in anteriores
    ]
    recuperado = recuperar_fragmentos(
        con,
        novel_id=novel_id,
        version=version,
        entidades=bc.entidades,
        antes_de=numero,
        excluir={numero - 1},
        maximo=config.umbrales.recuperacion.max_fragmentos,
    )
    presentes = {bc.pov, *(a["nombre"] for a in bc.alcance if a["tipo"] == "personaje")}
    estilo = [
        Pieza(
            etiqueta=f"Voz de {p.nombre}",
            texto=p.voz or "",
            prioridad=10 if p.nombre == bc.pov else 5,
        )
        for p in novel.personajes(con, novel_id=novel_id)
        if p.nombre in presentes and p.voz
    ]
    ventana = config.umbrales.contexto.anticontexto_ventana_capitulos
    anticontexto = piezas_anticontexto(
        config,
        brief,
        palabras_novela=palabras_novela,
        textos_recientes=[c.texto for c in anteriores[-ventana:]],
    )
    return {
        "invariante": piezas_invariante(brief),
        "estructural": estructural,
        "estado": estado,
        "local": local,
        "recuperado": recuperado,
        "estilo": estilo,
        "anticontexto": anticontexto,
    }


def piezas_judge(
    con: sqlite3.Connection,
    config: Config,
    *,
    novel_id: str,
    version: int,
    numero: int,
    brief: BriefNovela,
    brief_capitulo: BriefCapitulo,
    titulo: str,
    texto: str,
) -> dict[str, list[Pieza]]:
    """El contexto del judge: lo que la rúbrica necesita para puntuar un borrador.

    El borrador va en Local como dato no confiable: es salida del modelo escrita sobre texto
    del comprador, y nada de él puede cerrar una etiqueta ni pasar por instrucción.
    """
    bc = brief_capitulo
    invariante = piezas_invariante(brief)
    if brief.temas_excluidos:
        invariante.append(
            Pieza(
                etiqueta="Temas excluidos",
                texto="\n".join(f"- {t}" for t in brief.temas_excluidos),
                prioridad=10,
            )
        )
    ultimo = numero == config.umbrales.obra.capitulos
    estructural = [
        Pieza(
            etiqueta=f"Brief del capítulo {numero}",
            texto="\n".join(
                [
                    f"Función dramática: {bc.funcion_dramatica}",
                    f"Punto de vista: {bc.pov}",
                    f"Lugar: {bc.lugar}",
                    f"Restricción de destino: [{bc.restriccion_tipo}] {bc.restriccion_enunciado}",
                    "Es el último capítulo: el arco se cierra aquí."
                    if ultimo
                    else f"Capítulo {numero} de {config.umbrales.obra.capitulos}.",
                ]
            ),
            prioridad=10,
        )
    ]
    estado = [Pieza(etiqueta="Estado de entrada", texto=bc.estado_entrada, prioridad=10)]
    previos = [
        c
        for c in novel.capitulos_aceptados(con, novel_id=novel_id, version=version)
        if c.numero < numero
    ]
    if previos:
        snapshot = canon.snapshot_de(
            con, novel_id=novel_id, version=version, capitulo_id=previos[-1].capitulo_id
        )
        if snapshot is not None:
            estado.append(Pieza(texto=_render_snapshot(snapshot), prioridad=9))
    local = [
        Pieza(
            etiqueta=f"Capítulo {numero} a evaluar: {titulo}",
            texto=texto,
            no_confiable=True,
            prioridad=100,
        )
    ]
    return {
        "invariante": invariante,
        "estructural": estructural,
        "estado": estado,
        "local": local,
        "recuperado": [],
        "estilo": [],
        "anticontexto": [],
    }


def piezas_editor(
    con: sqlite3.Connection,
    config: Config,
    *,
    novel_id: str,
    version: int,
    numero: int,
    brief: BriefNovela,
    brief_capitulo: BriefCapitulo,
    palabras_novela: list[str],
    titulo: str,
    texto: str,
    informe: list[str],
) -> dict[str, list[Pieza]]:
    """El contexto del editor: el del judge, más el informe de crítica y el anticontexto.

    El informe cita fragmentos del borrador, así que va igual que él: como dato no confiable.
    """
    piezas = piezas_judge(
        con,
        config,
        novel_id=novel_id,
        version=version,
        numero=numero,
        brief=brief,
        brief_capitulo=brief_capitulo,
        titulo=titulo,
        texto=texto,
    )
    piezas["local"] = [
        Pieza(
            etiqueta=f"Capítulo {numero} a corregir: {titulo}",
            texto=texto,
            no_confiable=True,
            prioridad=100,
        )
    ]
    piezas["estructural"].append(
        Pieza(
            etiqueta="Informe de crítica: defectos que corregir",
            texto="\n".join(f"- {d}" for d in informe),
            no_confiable=True,
            prioridad=10,
        )
    )
    cap = config.umbrales.capitulo
    piezas["estructural"].append(
        Pieza(
            etiqueta="Longitud",
            texto=f"De {cap.longitud_min_palabras} a {cap.longitud_max_palabras} palabras.",
            prioridad=10,
        )
    )
    anteriores = [
        c.texto
        for c in novel.capitulos_aceptados(con, novel_id=novel_id, version=version)
        if c.numero < numero
    ]
    piezas["anticontexto"] = piezas_anticontexto(
        config,
        brief,
        palabras_novela=palabras_novela,
        textos_recientes=anteriores[-config.umbrales.contexto.anticontexto_ventana_capitulos :],
    )
    return piezas
