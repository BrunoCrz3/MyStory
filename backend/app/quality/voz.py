"""Voz narrativa, POV y distintividad de voz.

`P-42` da la persona y el tiempo verbal por deterministas: dejan marca
morfologica y se leen con una lista cerrada de terminaciones. El punto ciego
declarado se asume — el cambio de distancia o de focalizacion dentro del mismo
tiempo verbal no deja marca, y ahi esto no llega.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from app.commons.db.conexion import Conexion
from app.context import service as contexto
from app.novel import models as novel_models
from app.novel import service as novel
from app.quality.schemas import DefectoDetectado, PeticionDeCritica

PRONOMBRES_DE_PRIMERA = frozenset({"yo", "nosotros", "nosotras"})
FIN_DE_PRIMERA = ("é", "í")

MARCAS_DE_PASADO = re.compile(r"\b\w+(ó|aron|ieron|aba|aban|ía|ían)\b", re.IGNORECASE)
IRREGULARES_DE_PASADO = frozenset(
    {"dijo", "fue", "fueron", "tuvo", "hizo", "vino", "puso", "pudo", "supo", "estuvo"}
)
MARCAS_DE_PRESENTE = frozenset(
    {
        "es",
        "está",
        "tiene",
        "hace",
        "dice",
        "va",
        "viene",
        "cruza",
        "mira",
        "sabe",
        "entra",
        "puede",
        "quiere",
        "llega",
        "abre",
        "siente",
        "piensa",
    }
)

# Verbos de acceso mental. Una fuga de POV es uno de estos con un sujeto que no
# es el punto de vista de la escena.
ACCESO_MENTAL = frozenset(
    {
        "pensó",
        "sintió",
        "supo",
        "temió",
        "creyó",
        "recordó",
        "deseó",
        "imaginó",
        "comprendió",
        "intuyó",
        "sospechó",
    }
)

MUESTRAS_MINIMAS_POR_VOZ = 2


def _norma(texto: str) -> str:
    return "".join(
        letra
        for letra in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(letra) != "Mn"
    )


def _palabras(texto: str) -> list[str]:
    return re.findall(r"[a-zñáéíóúü]+", texto.lower())


def _frases(texto: str) -> list[str]:
    return [frase.strip() for frase in re.split(r"(?<=[.!?…])\s+", texto) if frase.strip()]


def persona_detectada(texto: str) -> str:
    palabras = _palabras(texto)
    primera = any(palabra in PRONOMBRES_DE_PRIMERA for palabra in palabras) or any(
        len(palabra) >= 3 and palabra.endswith(FIN_DE_PRIMERA) for palabra in palabras
    )
    return "primera" if primera else "tercera"


def tiempo_detectado(texto: str) -> str | None:
    """`None` cuando el texto no trae marca suficiente para decidir."""
    palabras = _palabras(texto)
    pasado = len(MARCAS_DE_PASADO.findall(texto)) + sum(
        1 for palabra in palabras if palabra in IRREGULARES_DE_PASADO
    )
    presente = sum(1 for palabra in palabras if palabra in MARCAS_DE_PRESENTE)
    if pasado == presente:
        return None
    return "pasado" if pasado > presente else "presente"


def verificar(base: Conexion, peticion: PeticionDeCritica) -> list[DefectoDetectado]:
    """P-42, P-11, RF-QUA-09."""
    declaradas = novel.listar(base, novel_models.VozNarrativa)
    defectos: list[DefectoDetectado] = []

    if declaradas:
        voz = declaradas[0]
        if voz.persona and persona_detectada(peticion.texto) != _norma(voz.persona):
            defectos.append(
                DefectoDetectado(
                    dimension="integridad_de_pov",
                    gravedad="alta",
                    descripcion=(
                        f"la persona del borrador no es la declarada en Voz narrativa "
                        f"(«{voz.persona}»)"
                    ),
                )
            )
        detectado = tiempo_detectado(peticion.texto)
        if voz.tiempo_verbal and detectado and detectado != _norma(voz.tiempo_verbal):
            defectos.append(
                DefectoDetectado(
                    dimension="integridad_de_pov",
                    gravedad="alta",
                    descripcion=(
                        f"el tiempo verbal del borrador es «{detectado}» y Voz narrativa "
                        f"declara «{voz.tiempo_verbal}»"
                    ),
                )
            )

    defectos += _fugas_de_pov(base, peticion)
    return defectos


def _fugas_de_pov(base: Conexion, peticion: PeticionDeCritica) -> list[DefectoDetectado]:
    """Una escena tiene un solo POV.

    El punto ciego declarado se asume: detecta el verbo de acceso ajeno («supo
    que ella temia»); no detecta la fuga por descripcion de lo que el POV no
    puede ver.
    """
    if peticion.pov_personaje_id is None:
        return []
    nombres = {
        personaje.id: personaje.nombre for personaje in novel.listar(base, novel_models.Personaje)
    }
    del_pov = _norma(nombres.get(peticion.pov_personaje_id, ""))

    defectos: list[DefectoDetectado] = []
    for frase in _frases(peticion.texto):
        for palabra in _palabras(frase):
            if palabra not in ACCESO_MENTAL:
                continue
            sujeto = _sujeto_antes_de(frase, palabra, nombres)
            if sujeto is not None and _norma(sujeto) != del_pov:
                defectos.append(
                    DefectoDetectado(
                        dimension="integridad_de_pov",
                        gravedad="alta",
                        localizacion=frase,
                        descripcion=(
                            f"acceso mental de {sujeto} en una escena cuyo POV es "
                            f"{nombres.get(peticion.pov_personaje_id, 'otro')}"
                        ),
                    )
                )
    return defectos


def _sujeto_antes_de(frase: str, verbo: str, nombres: dict[int, str]) -> str | None:
    normalizada = _norma(frase)
    posicion = normalizada.find(_norma(verbo))
    if posicion < 0:
        return None
    anterior = normalizada[:posicion]
    candidatos = [
        nombre for nombre in nombres.values() if _norma(nombre) and _norma(nombre) in anterior
    ]
    if not candidatos:
        return None
    return max(candidatos, key=lambda nombre: anterior.rfind(_norma(nombre)))


# --- P-08: clasificador ciego con el propio corpus ------------------------


@dataclass(frozen=True)
class MedidaDeVoz:
    evaluados: int
    aciertos: int
    acierto: float | None
    azar: float


def clasificacion_ciega(base: Conexion, personajes: list[int], escena_id: int) -> MedidaDeVoz:
    """Solucion picara #10, para `P-08`.

    Clasificador entrenado sobre el dialogo ya aceptado de la obra y evaluado
    **dejando fuera** la muestra que se juzga. Determinista, sin semilla y sin
    anotador: si no acierta quien habla por encima del azar, las voces no estan
    diferenciadas.

    **No cierra la pregunta abierta #6.** Quien clasifica lo decide el autor;
    esto es el candidato barato. Si el autor elige a una persona, `P-08` pasa a
    `D` y sale de v1.
    """
    azar = 1 / len(personajes) if personajes else 0.0
    muestras: list[tuple[int, Counter[str]]] = []
    for personaje in personajes:
        for fragmento in contexto.muestras_de_voz(base, [personaje], escena_id, cuantas=50):
            muestras.append((personaje, Counter(_palabras(fragmento.texto))))

    # Con menos de dos voces no hay a quien confundir, asi que no hay nada que
    # clasificar: sin este corte, una escena sin personajes presentes declarados
    # entra en el bucle con la lista vacia y la division final revienta.
    if len(personajes) < 2:
        return MedidaDeVoz(evaluados=0, aciertos=0, acierto=None, azar=azar)

    por_voz = Counter(personaje for personaje, _ in muestras)
    if any(por_voz[personaje] < MUESTRAS_MINIMAS_POR_VOZ for personaje in personajes):
        return MedidaDeVoz(evaluados=0, aciertos=0, acierto=None, azar=azar)

    aciertos = 0
    for indice, (verdadero, bolsa) in enumerate(muestras):
        centroides = _centroides(muestras, excluyendo=indice)
        elegido = max(centroides, key=lambda voz: _coseno(bolsa, centroides[voz]))
        aciertos += int(elegido == verdadero)

    return MedidaDeVoz(
        evaluados=len(muestras),
        aciertos=aciertos,
        acierto=aciertos / len(muestras),
        azar=azar,
    )


def _centroides(
    muestras: list[tuple[int, Counter[str]]], excluyendo: int
) -> dict[int, Counter[str]]:
    centroides: dict[int, Counter[str]] = {}
    for indice, (personaje, bolsa) in enumerate(muestras):
        if indice == excluyendo:
            continue
        centroides.setdefault(personaje, Counter()).update(bolsa)
    return centroides


def _coseno(uno: Counter[str], otro: Counter[str]) -> float:
    comunes = set(uno) & set(otro)
    producto = sum(uno[palabra] * otro[palabra] for palabra in comunes)
    norma = math.sqrt(sum(v * v for v in uno.values())) * math.sqrt(
        sum(v * v for v in otro.values())
    )
    return 0.0 if norma == 0 else producto / norma
