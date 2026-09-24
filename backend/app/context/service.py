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

from app.commons.config import Config
from app.context import repository
from app.context.ensamblador import Contador, Ensamblado, Ensamblador, Pieza
from app.context.fuentes import ContadorProveedor, expresiones_repetidas, recuperar_fragmentos
from app.guardrail import service as guardrail
from app.intake.service import BriefNovela

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
