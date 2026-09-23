"""`verificar-continuidad`: contrasta el borrador contra el canon vigente en `t`.

Cinco ejes, todos resueltos con una consulta contra estado que el canon ya
guarda. Son baratos y no esperan a ningun umbral, que es por lo que entran en v1
mientras las dimensiones que necesitan juicio siguen midiendo sin suspender.

**Todo esto cruza nombres propios y terminos canonicos.** Es la solucion picara
#4 —glosario cerrado— llevada al verificador, y su limite esta declarado en cada
fila de `verification.md`: lo que la escena dice sin nombrar a nadie no lo ve
nadie.

El eje temporal no esta. No es un olvido: `Evento.momento_en_la_fabula` es texto
libre y no hay relacion `Lugar`-`Lugar` con coste de desplazamiento, asi que no
hay orden contra el que comprobar una cronologia. Las dos carencias son del
documento vivo y estan listadas en `verification.md` § Filas pendientes de
ontologia.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.canon import service as canon
from app.canon.models import HechoCanonico, TipoDeHecho
from app.commons.db.conexion import Conexion
from app.novel import models as novel_models
from app.novel import service as novel
from app.quality.models import Eje
from app.quality.schemas import DefectoDetectado, PeticionDeCritica

# Cuantas letras bastan para dar dos palabras por la misma. Cubre la flexion sin
# necesitar un lematizador: «habla», «hablo», «hablaba».
PREFIJO = 4
LONGITUD_MINIMA = 3

NEGACIONES = ("nunca", "jamas", " no ", "ninguna vez", "tampoco")
VERBOS_DE_POSESION = ("saco", "tenia", "llevaba", "cogio", "entrego", "guardaba", "robo")
VERBOS_DE_SABER = ("sabia", "sabe", "conocia", "conoce", "recordaba", "recuerda")
VERBOS_DE_PREGUNTAR = ("pregunto", "pregunta", "ignoraba", "desconocia", "quiso saber")

# Marca morfologica de accion en pasado. `P-42` da la persona y el tiempo por
# deterministas; esto es esa misma marca, aplicada sobre el texto con tildes.
ACCION_EN_PASADO = re.compile(r"\b\w+(ó|aron|ieron|aba|ía)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Entidades:
    personajes: dict[int, str]
    lugares: dict[int, str]
    artefactos: dict[int, str]


def _norma(texto: str) -> str:
    return "".join(
        letra
        for letra in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(letra) != "Mn"
    )


def _frases(texto: str) -> list[str]:
    return [frase.strip() for frase in re.split(r"(?<=[.!?…])\s+", texto) if frase.strip()]


def _nombra(normalizado: str, nombre: str) -> bool:
    return _norma(nombre) in normalizado


def terminos(texto: str) -> set[str]:
    """Raices de cuatro letras. Cubre la flexion sin lematizador."""
    return {
        palabra[:PREFIJO]
        for palabra in re.findall(r"[a-zñ]+", _norma(texto))
        if len(palabra) >= LONGITUD_MINIMA
    }


def entidades_de_la_obra(base: Conexion) -> Entidades:
    return Entidades(
        personajes={p.id: p.nombre for p in novel.listar(base, novel_models.Personaje)},
        lugares={lugar.id: lugar.nombre for lugar in novel.listar(base, novel_models.Lugar)},
        artefactos={a.id: a.nombre for a in novel.listar(base, novel_models.Artefacto)},
    )


def verificar(base: Conexion, peticion: PeticionDeCritica) -> list[DefectoDetectado]:
    entidades = entidades_de_la_obra(base)
    vigentes = canon.hechos_vigentes_en(base, peticion.escena_id)
    frases = _frases(peticion.texto)

    return [
        *_factica(base, peticion, frases, vigentes, entidades),
        *_espacial(frases, vigentes, entidades),
        *_epistemica(base, peticion, frases, vigentes, entidades),
        *_especulativa(base, peticion),
    ]


def _factica(
    base: Conexion,
    peticion: PeticionDeCritica,
    frases: list[str],
    vigentes: list[HechoCanonico],
    entidades: Entidades,
) -> list[DefectoDetectado]:
    """P-02, P-37, P-38."""
    defectos: list[DefectoDetectado] = []
    snapshot = canon.snapshot_en(base, peticion.escena_id)

    # P-02: el borrador niega explicitamente un hecho vigente. Solo llega a lo
    # enunciado con terminos canonicos y nombres propios.
    for frase in frases:
        normalizada = f" {_norma(frase)} "
        if not any(negacion in normalizada for negacion in NEGACIONES):
            continue
        for hecho in vigentes:
            anclas = _anclas_de(hecho, entidades)
            if anclas and all(_nombra(normalizada, ancla) for ancla in anclas):
                defectos.append(
                    DefectoDetectado(
                        dimension="consistencia_factica",
                        eje=Eje.FACTICA,
                        gravedad="alta",
                        localizacion=frase,
                        descripcion=f"el borrador niega el hecho vigente {hecho.id}",
                    )
                )

    # P-37: ningun personaje no vivo actua.
    for personaje_id, nombre in entidades.personajes.items():
        if personaje_id in snapshot.personajes_vivos or not _no_vivo(vigentes, personaje_id):
            continue
        for frase in frases:
            if _nombra(_norma(frase), nombre) and _actua(frase, nombre):
                defectos.append(
                    DefectoDetectado(
                        dimension="consistencia_factica",
                        eje=Eje.FACTICA,
                        gravedad="alta",
                        localizacion=frase,
                        descripcion=(
                            f"{nombre} no esta vivo en el snapshot en t y actua en el borrador"
                        ),
                    )
                )
                break

    # P-38: ningun artefacto cambia de poseedor sin escena que lo establezca.
    for artefacto_id, poseedor in snapshot.posesiones.items():
        artefacto = entidades.artefactos.get(artefacto_id)
        if artefacto is None:
            continue
        for frase in frases:
            normalizada = _norma(frase)
            if not _nombra(normalizada, artefacto):
                continue
            if not any(verbo in normalizada for verbo in VERBOS_DE_POSESION):
                continue
            intrusos = [
                otro
                for identificador, otro in entidades.personajes.items()
                if identificador != poseedor and _nombra(normalizada, otro)
            ]
            if intrusos:
                defectos.append(
                    DefectoDetectado(
                        dimension="consistencia_factica",
                        eje=Eje.FACTICA,
                        gravedad="alta",
                        localizacion=frase,
                        descripcion=(
                            f"«{nombre}» pasa a manos de {intrusos[0]} sin escena que lo establezca"
                        ),
                    )
                )
    return defectos


def _espacial(
    frases: list[str], vigentes: list[HechoCanonico], entidades: Entidades
) -> list[DefectoDetectado]:
    """P-04.

    El punto ciego declarado se asume: sabe donde estaba el personaje, no cuanto
    tarda en llegar. Sin coste de desplazamiento entre `Lugar` —que la ontologia
    no modela—, un desplazamiento imposible es indistinguible de uno lento.
    """
    defectos: list[DefectoDetectado] = []
    ubicaciones = {
        hecho.sujeto_personaje_id: hecho.lugar_id
        for hecho in vigentes
        if hecho.tipo is TipoDeHecho.UBICACION
        and hecho.sujeto_personaje_id is not None
        and hecho.lugar_id is not None
    }

    for personaje_id, lugar_id in ubicaciones.items():
        nombre = entidades.personajes.get(personaje_id)
        vigente = entidades.lugares.get(lugar_id)
        if nombre is None or vigente is None:
            continue
        for frase in frases:
            normalizada = _norma(frase)
            if not _nombra(normalizada, nombre) or _nombra(normalizada, vigente):
                continue
            otros = [
                otro
                for identificador, otro in entidades.lugares.items()
                if identificador != lugar_id and _nombra(normalizada, otro)
            ]
            if otros:
                defectos.append(
                    DefectoDetectado(
                        dimension="consistencia_espacial",
                        eje=Eje.ESPACIAL,
                        gravedad="media",
                        localizacion=frase,
                        descripcion=(
                            f"{nombre} aparece en «{otros[0]}» y el snapshot en t lo situa "
                            f"en «{vigente}»"
                        ),
                    )
                )
    return defectos


def _epistemica(
    base: Conexion,
    peticion: PeticionDeCritica,
    frases: list[str],
    vigentes: list[HechoCanonico],
    entidades: Entidades,
) -> list[DefectoDetectado]:
    """P-05 y P-51, los dos sentidos, mas P-40.

    «Ni usar lo que no se sabe ni ignorar lo que si». La segunda mitad es la que
    casi nadie implementa, y es la que produce el personaje que se sorprende dos
    veces de lo mismo.
    """
    defectos: list[DefectoDetectado] = []
    conocimiento = {
        personaje_id: {
            estado.hecho_id for estado in canon.que_sabe(base, personaje_id, peticion.escena_id)
        }
        for personaje_id in entidades.personajes
    }

    for frase in frases:
        normalizada = _norma(frase)
        usa = any(verbo in normalizada for verbo in VERBOS_DE_SABER)
        pregunta = any(verbo in normalizada for verbo in VERBOS_DE_PREGUNTAR)
        if not (usa or pregunta):
            continue
        for hecho in vigentes:
            contenido = _norma(hecho.valor or "")
            if not contenido or contenido not in normalizada:
                continue
            for personaje_id, nombre in entidades.personajes.items():
                if not _nombra(normalizada, nombre):
                    continue
                sabidos = conocimiento[personaje_id]
                if usa and hecho.id not in sabidos:
                    defectos.append(
                        DefectoDetectado(
                            dimension="consistencia_epistemica",
                            eje=Eje.EPISTEMICA,
                            gravedad="alta",
                            localizacion=frase,
                            descripcion=(
                                f"{nombre} usa el hecho {hecho.id} y su estado epistemico no "
                                "lo registra"
                            ),
                        )
                    )
                if pregunta and hecho.id in sabidos:
                    defectos.append(
                        DefectoDetectado(
                            dimension="consistencia_epistemica",
                            eje=Eje.EPISTEMICA,
                            gravedad="media",
                            localizacion=frase,
                            descripcion=(
                                f"{nombre} pregunta por el hecho {hecho.id}, que su estado "
                                "epistemico ya registra"
                            ),
                        )
                    )

    texto = _norma(peticion.texto)
    for revelacion in canon.revelaciones_pendientes(base, peticion.escena_id):
        contenido = _norma(revelacion.valor or "")
        if contenido and contenido in texto:
            defectos.append(
                DefectoDetectado(
                    dimension="consistencia_epistemica",
                    eje=Eje.EPISTEMICA,
                    gravedad="alta",
                    descripcion=(
                        f"la revelacion del hecho {revelacion.hecho_id} llega por debajo "
                        "de su escena minima permitida"
                    ),
                )
            )
    return defectos


def _especulativa(base: Conexion, peticion: PeticionDeCritica) -> list[DefectoDetectado]:
    """P-07: el novum no viola sus propias reglas.

    Solo alcanza a las reglas **declaradas** con la forma «X solo Y»: si el
    texto trae el sujeto de la regla, tiene que traer tambien su condicion. Una
    consecuencia en cascada que nadie escribio no la ve nadie, y eso esta
    declarado en la fila.
    """
    defectos: list[DefectoDetectado] = []
    del_texto = terminos(peticion.texto)

    for regla in novel.listar(base, novel_models.ReglaDelMundo):
        enunciado = _norma(regla.enunciado)
        if " solo " not in enunciado:
            continue
        sujeto, condicion = enunciado.split(" solo ", 1)
        # La condicion vinculante es la cola: «solo habla **en crecida**».
        terminos_del_sujeto = terminos(sujeto)
        terminos_de_la_condicion = terminos(" ".join(condicion.split()[-2:]))
        if not terminos_del_sujeto or not terminos_de_la_condicion:
            continue
        if terminos_del_sujeto <= del_texto and not (terminos_de_la_condicion & del_texto):
            defectos.append(
                DefectoDetectado(
                    dimension="plausibilidad_especulativa",
                    eje=Eje.ESPECULATIVA,
                    gravedad="alta",
                    descripcion=(
                        f"el borrador ocurre sin la condicion que exige la regla "
                        f"«{regla.enunciado}»"
                    ),
                )
            )
    return defectos


def _anclas_de(hecho: HechoCanonico, entidades: Entidades) -> list[str]:
    """Nombres propios con los que el hecho se puede reconocer en el texto."""
    anclas = [
        nombre
        for nombre in (
            entidades.personajes.get(hecho.sujeto_personaje_id or 0),
            entidades.lugares.get(hecho.lugar_id or 0),
            entidades.artefactos.get(hecho.artefacto_id or 0),
        )
        if nombre
    ]
    return anclas


def _no_vivo(vigentes: list[HechoCanonico], personaje_id: int) -> bool:
    return any(
        hecho.tipo is TipoDeHecho.ESTADO_VITAL
        and hecho.sujeto_personaje_id == personaje_id
        and (hecho.valor or "") == "muerto"
        for hecho in vigentes
    )


def _actua(frase: str, nombre: str) -> bool:
    posicion = _norma(frase).find(_norma(nombre))
    if posicion < 0:
        return False
    return bool(ACCION_EN_PASADO.search(frase[posicion + len(nombre) :]))
