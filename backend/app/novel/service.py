"""Servicio de la obra. Crea la novela con su brief, sin lanzar la generación
(RF-INTAKE-04), y la sirve (RF-NOVEL-02, RF-NOVEL-03)."""

from __future__ import annotations

import sqlite3
import uuid

from pydantic import BaseModel, ConfigDict

from app.commons.config import Config
from app.commons.db import BaseDatos
from app.commons.errores import NovelaNoEncontrada
from app.commons.texto import contar_palabras
from app.commons.tiempo import ahora
from app.guardrail import service as guardrail
from app.intake import service as intake
from app.intake.service import BriefNovela
from app.novel import repository
from app.novel.models import (
    ESTADOS_TERMINALES_NOVELA,
    EstadoCapitulo,
    EstadoNovela,
    EventoNarrado,
    EventoVigente,
    HiloTrama,
    Lugar,
    Personaje,
    PresenciaEnEvento,
    ReglaMundo,
)
from app.novel.schemas import ListaNovelas, Novela, NovelaResumen

__all__ = [
    "ESTADOS_TERMINALES_NOVELA",
    "CapituloAceptado",
    "CapituloEnCurso",
    "EstadoCapitulo",
    "EstadoNovela",
    "EventoNarrado",
    "EventoVigente",
    "HiloTrama",
    "Lugar",
    "Personaje",
    "ReglaMundo",
    "capitulo_en_curso",
    "capitulos_aceptados",
    "contar_aceptados",
    "crear_capitulo",
    "crear_novela",
    "estado_de_obra",
    "eventos_de_version",
    "fijar_estado_capitulo",
    "fijar_estado_obra",
    "fijar_titulo",
    "guardar_texto_aceptado",
    "listar_novelas",
    "lugares",
    "nombres_de_la_obra",
    "obtener_novela",
    "personajes",
    "registrar_elementos_en_capitulo",
    "registrar_eventos",
    "registrar_reparto",
    "reglas_del_mundo",
    "retirar_eventos",
    "revertir_eventos",
    "sumar_consumo",
    "titulo_de_obra",
    "total_capitulos",
    "version_vigente",
]


def _version_vigente(con: sqlite3.Connection, *, novel_id: str) -> int | None:
    fila = con.execute(
        # Solo una publicada es la vigente: una candidata o una rechazada, nunca (RNF-19).
        "SELECT max(version) FROM version_novela WHERE novel_id = ? AND estado = 'publicada'",
        (novel_id,),
    ).fetchone()
    valor: int | None = fila[0]
    return valor


def _novela(con: sqlite3.Connection, *, novel_id: str) -> Novela:
    obra = repository.leer_obra(con, novel_id=novel_id)
    brief = intake.leer_brief(con, novel_id=novel_id)
    if obra is None or brief is None:
        raise NovelaNoEncontrada(f"no existe la novela {novel_id}", novel_id=novel_id)
    return Novela(
        novel_id=obra["novel_id"],
        titulo=obra["titulo"],
        estado=obra["estado"],
        version_vigente=_version_vigente(con, novel_id=novel_id),
        total_capitulos=obra["total_capitulos"],
        creada_en=obra["creada_en"],
        brief=brief,
    )


async def crear_novela(db: BaseDatos, config: Config, brief: BriefNovela) -> Novela:
    intake.exigir_brief_valido(config, brief)
    novel_id = str(uuid.uuid4())
    momento = ahora()

    def escribir(con: sqlite3.Connection) -> Novela:
        repository.insertar_obra(
            con,
            novel_id=novel_id,
            brief=brief,
            total=config.umbrales.obra.capitulos,
            ahora=momento,
        )
        intake.registrar_brief(con, novel_id=novel_id, brief=brief, ahora=momento)
        guardrail.registrar_palabras_novela(
            con, novel_id=novel_id, palabras=brief.palabras_prohibidas
        )
        return _novela(con, novel_id=novel_id)

    return await db.en_transaccion(escribir)


async def obtener_novela(db: BaseDatos, novel_id: str) -> Novela:
    return await db.ejecutar(lambda con: _novela(con, novel_id=novel_id))


async def listar_novelas(db: BaseDatos, *, limite: int, desplazamiento: int) -> ListaNovelas:
    def leer(con: sqlite3.Connection) -> ListaNovelas:
        filas = repository.listar_obras(con, limite=limite, desplazamiento=desplazamiento)
        return ListaNovelas(
            items=[
                NovelaResumen(
                    novel_id=f["novel_id"],
                    titulo=f["titulo"],
                    estado=f["estado"],
                    version_vigente=_version_vigente(con, novel_id=f["novel_id"]),
                    creada_en=f["creada_en"],
                )
                for f in filas
            ],
            total=repository.contar_obras(con),
        )

    return await db.ejecutar(leer)


def reglas_del_mundo(con: sqlite3.Connection, *, novel_id: str) -> list[ReglaMundo]:
    return repository.leer_reglas(con, novel_id=novel_id)


def crear_capitulo(
    con: sqlite3.Connection, *, novel_id: str, numero: int, version: int, estado: str = "Pendiente"
) -> str:
    """Crea la fila del capítulo `numero` para la versión `version` (D-05): en `Pendiente`, o en
    `Obsoleto` si es la de un capítulo afectado en la candidata de una regeneración (TO-062)."""
    return repository.insertar_capitulo(
        con, novel_id=novel_id, numero=numero, version=version, estado=estado
    )


class CapituloAceptado(BaseModel):
    model_config = ConfigDict(frozen=True)

    capitulo_id: str
    numero: int
    titulo: str | None
    texto: str


def capitulos_aceptados(
    con: sqlite3.Connection, *, novel_id: str, version: int
) -> list[CapituloAceptado]:
    """Los capítulos aceptados que lee una versión, en orden (memoria episódica)."""
    return [
        CapituloAceptado(
            capitulo_id=f["id"], numero=f["numero"], titulo=f["titulo"], texto=f["texto"]
        )
        for f in repository.leer_capitulos_aceptados(con, novel_id=novel_id, version=version)
    ]


def fijar_titulo(con: sqlite3.Connection, *, novel_id: str, titulo: str, premisa: str) -> None:
    repository.fijar_titulo(con, novel_id=novel_id, titulo=titulo, premisa=premisa)


def registrar_reparto(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    personajes: list[Personaje],
    lugares: list[Lugar],
    hilos: list[HiloTrama],
) -> None:
    for p in personajes:
        repository.insertar_personaje(
            con,
            novel_id=novel_id,
            nombre=p.nombre,
            deseo=p.deseo or "",
            herida=p.herida or "",
            rol_narrativo=p.rol_narrativo or "",
            voz=p.voz or "",
            es_destinatario=p.es_destinatario,
            fecha_nacimiento=p.fecha_nacimiento,
        )
    for lugar in lugares:
        repository.insertar_lugar(
            con,
            novel_id=novel_id,
            nombre=lugar.nombre,
            geografia=lugar.geografia or "",
            atmosfera=lugar.atmosfera or "",
        )
    for h in hilos:
        repository.insertar_hilo(
            con, novel_id=novel_id, nombre=h.nombre, pregunta_dramatica=h.pregunta_dramatica or ""
        )


def personajes(con: sqlite3.Connection, *, novel_id: str) -> list[Personaje]:
    return [
        Personaje(
            nombre=f["nombre"],
            deseo=f["deseo"],
            herida=f["herida"],
            rol_narrativo=f["rol_narrativo"],
            voz=f["voz"],
            es_destinatario=bool(f["es_destinatario"]),
            fecha_nacimiento=f["fecha_nacimiento"],
        )
        for f in repository.leer_personajes(con, novel_id=novel_id)
    ]


def lugares(con: sqlite3.Connection, *, novel_id: str) -> list[Lugar]:
    return [
        Lugar(nombre=f["nombre"], geografia=f["geografia"], atmosfera=f["atmosfera"])
        for f in repository.leer_lugares(con, novel_id=novel_id)
    ]


class CapituloEnCurso(BaseModel):
    model_config = ConfigDict(frozen=True)

    capitulo_id: str
    numero: int
    version: int
    estado: str
    intentos: int


def capitulo_en_curso(
    con: sqlite3.Connection, *, novel_id: str, numero: int, version: int
) -> CapituloEnCurso | None:
    f = repository.leer_capitulo(con, novel_id=novel_id, numero=numero, version=version)
    if f is None:
        return None
    return CapituloEnCurso(
        capitulo_id=f["id"],
        numero=f["numero"],
        version=f["version"],
        estado=f["estado"],
        intentos=f["intentos"],
    )


def fijar_estado_capitulo(
    con: sqlite3.Connection, *, novel_id: str, capitulo_id: str, estado: str, intentos: int
) -> None:
    """Escribe el estado que ha decidido la máquina de estados de `process/`."""
    repository.actualizar_estado_capitulo(
        con, novel_id=novel_id, capitulo_id=capitulo_id, estado=estado, intentos=intentos
    )


def devolver_a_pendiente(
    con: sqlite3.Connection, *, novel_id: str, version: int, estados: tuple[str, ...]
) -> list[int]:
    """Reanudación: los capítulos en `estados` vuelven a `Pendiente` sin tocar sus intentos.

    No es una transición de la máquina: es deshacer un estado que ningún proceso vivo sostiene
    (TO-023). Devuelve los números normalizados.
    """
    return repository.devolver_a_pendiente(con, novel_id=novel_id, version=version, estados=estados)


def sumar_consumo(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    capitulo_id: str,
    tokens_entrada: int,
    tokens_salida: int,
    coste_usd: float,
) -> None:
    """Acumula tokens y coste de una llamada en su capítulo (RF-OBS-04)."""
    repository.sumar_consumo(
        con,
        novel_id=novel_id,
        capitulo_id=capitulo_id,
        tokens_entrada=tokens_entrada,
        tokens_salida=tokens_salida,
        coste_usd=coste_usd,
    )


def nombres_de_la_obra(con: sqlite3.Connection, *, novel_id: str) -> list[str]:
    """Nombres de personajes y lugares tal como los escribe la story bible."""
    return [p.nombre for p in personajes(con, novel_id=novel_id)] + [
        lugar.nombre for lugar in lugares(con, novel_id=novel_id)
    ]


def guardar_texto_aceptado(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    capitulo_id: str,
    titulo: str,
    texto: str,
    gancho_cierre: str,
    pov: str,
    lugar: str,
) -> None:
    """El texto de un capítulo solo se guarda al aceptarlo, en la transacción de consolidar."""
    repository.guardar_texto_aceptado(
        con,
        novel_id=novel_id,
        capitulo_id=capitulo_id,
        titulo=titulo,
        texto=texto,
        palabras=contar_palabras(texto),
        gancho_cierre=gancho_cierre,
        momento=ahora(),
        pov=pov,
        lugar=lugar,
    )


def registrar_eventos(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    version: int,
    capitulo_id: str,
    eventos: list[EventoNarrado],
) -> None:
    """Eventos de la fábula que narra el capítulo, vigentes desde `version` (TO-066), con sus
    personajes y su lugar. Un nombre que no está en la story bible se ignora: el extractor no
    crea entidades."""
    for e in eventos:
        repository.insertar_evento(
            con,
            novel_id=novel_id,
            capitulo_id=capitulo_id,
            version=version,
            descripcion=e.descripcion,
            momento=e.momento,
            lugar=e.lugar,
            personajes=e.personajes,
        )


def eventos_de_version(
    con: sqlite3.Connection, *, novel_id: str, version: int
) -> list[EventoVigente]:
    """La fábula de una versión: sus eventos vigentes en orden de narración, con quién está
    en cada uno y la edad que el texto le declara (TO-066)."""
    presentes: dict[str, list[PresenciaEnEvento]] = {}
    for evento_id, personaje_id, edad in repository.leer_presencias(
        con, novel_id=novel_id, version=version
    ):
        presentes.setdefault(evento_id, []).append(
            PresenciaEnEvento(personaje_id=personaje_id, edad=edad)
        )
    return [
        EventoVigente(
            evento_id=f["id"],
            capitulo_id=f["capitulo_id"],
            numero=f["numero"],
            momento=f["momento"],
            anio=f["anio"],
            lugar_id=f["lugar_id"],
            presentes=presentes.get(f["id"], []),
        )
        for f in repository.leer_eventos_de_version(con, novel_id=novel_id, version=version)
    ]


def retirar_eventos(
    con: sqlite3.Connection, *, novel_id: str, capitulo_id: str, version: int
) -> None:
    """Antes de reescribir un capítulo en `version`, sus eventos viejos se cierran ahí: la
    versión anterior conserva su fábula entera (TO-066, regla 15)."""
    repository.retirar_eventos(con, novel_id=novel_id, capitulo_id=capitulo_id, version=version)


def revertir_eventos(con: sqlite3.Connection, *, novel_id: str, version: int) -> None:
    """Una candidata rechazada no deja eventos vigentes en ninguna otra versión (TO-062)."""
    repository.revertir_eventos(con, novel_id=novel_id, version=version)


def registrar_elementos_en_capitulo(
    con: sqlite3.Connection, *, novel_id: str, capitulo_id: str, enunciados: list[str]
) -> None:
    """Qué elementos personalizados aparecen en el capítulo: sostiene `elementos_obligatorios`."""
    por_enunciado = {
        enunciado: eid
        for eid, enunciado, _ in intake.elementos_personalizados(con, novel_id=novel_id)
    }
    for enunciado in enunciados:
        if enunciado in por_enunciado:
            repository.insertar_elemento_en_capitulo(
                con,
                novel_id=novel_id,
                elemento_id=por_enunciado[enunciado],
                capitulo_id=capitulo_id,
            )


def estado_de_obra(con: sqlite3.Connection, *, novel_id: str) -> str | None:
    obra = repository.leer_obra(con, novel_id=novel_id)
    return None if obra is None else str(obra["estado"])


def titulo_de_obra(con: sqlite3.Connection, *, novel_id: str) -> str | None:
    obra = repository.leer_obra(con, novel_id=novel_id)
    return None if obra is None else obra["titulo"]


def total_capitulos(con: sqlite3.Connection, *, novel_id: str) -> int:
    obra = repository.leer_obra(con, novel_id=novel_id)
    if obra is None:
        raise NovelaNoEncontrada(f"no existe la novela {novel_id}", novel_id=novel_id)
    total: int = obra["total_capitulos"]
    return total


def fijar_estado_obra(con: sqlite3.Connection, *, novel_id: str, estado: str) -> None:
    """Escribe el estado que ha decidido la máquina de la novela de `process/`."""
    repository.actualizar_estado_obra(con, novel_id=novel_id, estado=estado)


def contar_aceptados(con: sqlite3.Connection, *, novel_id: str, version: int) -> int:
    """Capítulos escritos para `version` que ya están aceptados."""
    return repository.contar_aceptados(con, novel_id=novel_id, version=version)


def version_vigente(con: sqlite3.Connection, *, novel_id: str) -> int | None:
    return _version_vigente(con, novel_id=novel_id)


def estado_capitulo(con: sqlite3.Connection, *, novel_id: str, capitulo_id: str) -> str | None:
    return repository.leer_estado_capitulo(con, novel_id=novel_id, capitulo_id=capitulo_id)


def cambiar_estado_capitulo(
    con: sqlite3.Connection, *, novel_id: str, capitulo_id: str, estado: str
) -> None:
    """Escribe el estado que ha decidido la máquina de `process/` sin tocar los intentos."""
    repository.actualizar_solo_estado_capitulo(
        con, novel_id=novel_id, capitulo_id=capitulo_id, estado=estado
    )


def capitulo_vigente(
    con: sqlite3.Connection, *, novel_id: str, numero: int, version: int
) -> str | None:
    """La fila del capítulo `numero` que leía la novela antes de `version` (D-05)."""
    return repository.leer_capitulo_anterior(con, novel_id=novel_id, numero=numero, version=version)


def apariciones(
    con: sqlite3.Connection, *, novel_id: str, capitulo_ids: list[str]
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """En qué filas de capítulo aparece cada personaje y cada lugar (RF-VER-04)."""
    personajes, lugares = repository.leer_apariciones(
        con, novel_id=novel_id, capitulo_ids=capitulo_ids
    )
    por_personaje: dict[str, set[str]] = {}
    for nombre, cid in personajes:
        por_personaje.setdefault(nombre, set()).add(cid)
    por_lugar: dict[str, set[str]] = {}
    for nombre, cid in lugares:
        por_lugar.setdefault(nombre, set()).add(cid)
    return por_personaje, por_lugar
