"""`medir-calidad`: puntua las catorce dimensiones clasificadas `T`.

Dos cosas que conviene leer antes del codigo.

**Ninguna puntuacion esta calibrada.** Los catorce umbrales de
`config/thresholds.yaml` siguen en `null` y son `[mutacion]`: se calibran
inyectando defectos conocidos en escenas ya aceptadas (solucion picara #12), y
eso es RF-QUA-13, que queda fuera de v1. Mientras tanto estas cifras sirven para
comparar dos versiones de la misma escena —que es lo que pide A-50— y no para
decidir si una escena es buena.

**Dos dimensiones no se puntuan, y se dice por que.** `Originalidad` necesita
una linea base generada sin guia, que v1 no tiene, y `Consistencia temporal`
necesita un orden de fabula que la ontologia no declara. Devolver un numero
inventado seria peor que no devolverlo: entraria en el historial y contaminaria
la comparacion entre versiones.

La prosa se mide por codigo y el residuo se deja al critico (solucion picara
#11): eco de n-gramas, palabras filtro y varianza de frase no necesitan modelo.
"""

from __future__ import annotations

import re
import statistics
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

from app.commons.db.conexion import Conexion
from app.novel import models as novel_models
from app.novel import service as novel
from app.quality import continuidad, voz
from app.quality.schemas import DefectoDetectado, PeticionDeCritica

MEJOR = 1.0
PEOR = 0.0
# Cuanto baja una dimension por cada defecto encontrado en ella.
PENALIZACION_POR_DEFECTO = 0.25
LONGITUD_DEL_NGRAMA = 4

CONECTORES_CAUSALES = (
    "por tanto",
    "porque",
    "asi que",
    "de modo que",
    "sin embargo",
    "pero",
    "aunque",
    "por eso",
    "de ahi que",
)
CONECTORES_ADITIVOS = ("y entonces", "y luego", "y despues", "entonces", "luego")

PALABRAS_FILTRO = (
    "sintio que",
    "vio que",
    "noto que",
    "parecia que",
    "se dio cuenta de que",
    "empezo a",
    "comenzo a",
    "pudo ver",
    "logro ver",
)

MARCAS_DE_SUMARIO = (
    "durante anos",
    "durante meses",
    "solia",
    "cada dia",
    "cada noche",
    "con el tiempo",
    "semanas despues",
    "anos antes",
)

SIN_LINEA_BASE = (
    "no hay linea base generada sin guia contra la que medir la distancia; v1 la "
    "acumula y v2 la congela (RF-QUA-12, RF-QUA-13)"
)
SIN_ORDEN_DE_FABULA = (
    "`Evento.momento_en_la_fabula` es texto libre y no hay coste de desplazamiento "
    "entre `Lugar`: sin orden declarado no hay cronologia que comprobar "
    "(verification.md § Filas pendientes de ontologia)"
)
SIN_CORPUS_DE_VOZ = (
    "el clasificador ciego necesita dialogo ya aceptado de cada personaje y "
    "todavia no lo hay (solucion picara #10)"
)


@dataclass(frozen=True)
class Medida:
    valor: float | None
    motivo: str | None = None


@dataclass
class Aportacion:
    """Lo que devuelve un validador: puntuaciones y defectos."""

    puntuaciones: dict[str, Medida] = field(default_factory=dict)
    defectos: list[DefectoDetectado] = field(default_factory=list)


def _norma(texto: str) -> str:
    return "".join(
        letra
        for letra in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(letra) != "Mn"
    )


def _frases(texto: str) -> list[str]:
    return [frase.strip() for frase in re.split(r"(?<=[.!?…])\s+", texto) if frase.strip()]


def _palabras(texto: str) -> list[str]:
    return re.findall(r"[a-zñ]+", _norma(texto))


def _por_defectos(defectos: list[DefectoDetectado], dimension: str) -> Medida:
    cuantos = sum(1 for defecto in defectos if defecto.dimension == dimension)
    return Medida(valor=max(PEOR, MEJOR - PENALIZACION_POR_DEFECTO * cuantos))


# --- Los validadores ------------------------------------------------------


def validar_continuidad(base: Conexion, peticion: PeticionDeCritica) -> Aportacion:
    """RF-QUA-01: los ejes factico, espacial, epistemico y especulativo."""
    defectos = continuidad.verificar(base, peticion)
    dimensiones = (
        "consistencia_factica",
        "consistencia_espacial",
        "consistencia_epistemica",
        "plausibilidad_especulativa",
    )
    return Aportacion(
        puntuaciones={nombre: _por_defectos(defectos, nombre) for nombre in dimensiones},
        defectos=defectos,
    )


def validar_voz_narrativa(base: Conexion, peticion: PeticionDeCritica) -> Aportacion:
    """RF-QUA-09: persona, tiempo verbal y un solo POV."""
    defectos = voz.verificar(base, peticion)
    return Aportacion(
        puntuaciones={"integridad_de_pov": _por_defectos(defectos, "integridad_de_pov")},
        defectos=defectos,
    )


def validar_distintividad(base: Conexion, peticion: PeticionDeCritica) -> Aportacion:
    """P-08, solucion picara #10. Sin corpus no se puntua: se dice por que."""
    medida = voz.clasificacion_ciega(base, peticion.personajes_presentes, peticion.escena_id)
    if medida.acierto is None:
        return Aportacion(puntuaciones={"distintividad_de_voz": Medida(None, SIN_CORPUS_DE_VOZ)})
    # Por encima del azar es lo unico que significa algo: acertar la mitad con
    # dos voces es no distinguirlas.
    separacion = max(PEOR, (medida.acierto - medida.azar) / max(MEJOR - medida.azar, 1e-9))
    return Aportacion(puntuaciones={"distintividad_de_voz": Medida(round(separacion, 4))})


def validar_prosa(base: Conexion, peticion: PeticionDeCritica) -> Aportacion:
    """P-09, P-10, P-12, P-14, P-15. Todo por codigo, sin modelo."""
    del base
    texto = peticion.texto
    frases = _frases(texto)
    palabras = _palabras(texto)
    normalizado = _norma(texto)

    return Aportacion(
        puntuaciones={
            "calidad_de_prosa": Medida(_calidad_de_prosa(palabras, normalizado)),
            "mostrar_vs_contar": Medida(_mostrar_vs_contar(frases)),
            "causalidad": Medida(_causalidad(normalizado)),
            "ritmo": Medida(_ritmo(frases)),
        }
    )


def validar_carga_expositiva(base: Conexion, peticion: PeticionDeCritica) -> Aportacion:
    """P-15: infodumps y densidad de neologismos.

    Los neologismos del mundo son los `Termino canonico` declarados: es la
    solucion picara #4 —glosario cerrado— reutilizada para contar exposicion sin
    tener que adivinar que palabra es del mundo.
    """
    terminos = tuple(termino.forma for termino in novel.listar(base, novel_models.TerminoCanonico))
    palabras = _palabras(peticion.texto)
    return Aportacion(
        puntuaciones={
            "carga_expositiva": Medida(_carga_expositiva(terminos, palabras)),
        }
    )


def validar_cumplimiento_del_brief(base: Conexion, peticion: PeticionDeCritica) -> Aportacion:
    """P-18, solucion picara #5: la restriccion de destino es lo ejecutable.

    El punto ciego declarado se asume: cubre lo que el brief declara como
    restriccion; lo que pide en prosa —«que se note la tension entre ambos»— se
    queda fuera.
    """
    del base
    restriccion = peticion.restriccion_de_destino
    if not restriccion:
        return Aportacion(
            puntuaciones={
                "cumplimiento_del_brief": Medida(
                    None, "la peticion no declara restriccion de destino"
                )
            }
        )
    exigidos = continuidad.terminos(restriccion)
    presentes = exigidos & continuidad.terminos(peticion.texto)
    valor = len(presentes) / len(exigidos) if exigidos else MEJOR
    defectos = []
    if valor < MEJOR:
        defectos.append(
            DefectoDetectado(
                dimension="cumplimiento_del_brief",
                gravedad="media",
                descripcion=(
                    "la restriccion de destino no aparece entera en el borrador: faltan "
                    f"{sorted(exigidos - presentes)}"
                ),
            )
        )
    return Aportacion(
        puntuaciones={"cumplimiento_del_brief": Medida(round(valor, 4))}, defectos=defectos
    )


def validar_lo_que_v1_no_puede_medir(base: Conexion, peticion: PeticionDeCritica) -> Aportacion:
    """Las dos dimensiones `T` que v1 no puede puntuar, con su motivo.

    Estan aqui y no omitidas a proposito: RF-QUA-02 pide puntuar las catorce, y
    una dimension ausente del informe es indistinguible de una que se olvido.
    """
    del base, peticion
    return Aportacion(
        puntuaciones={
            "originalidad": Medida(None, SIN_LINEA_BASE),
            "consistencia_temporal": Medida(None, SIN_ORDEN_DE_FABULA),
        }
    )


# --- Metricas de prosa ----------------------------------------------------


def _calidad_de_prosa(palabras: list[str], normalizado: str) -> float:
    """Eco de n-gramas y palabras filtro. Solucion picara #11."""
    if not palabras:
        return PEOR
    ngramas = [
        tuple(palabras[indice : indice + LONGITUD_DEL_NGRAMA])
        for indice in range(max(len(palabras) - LONGITUD_DEL_NGRAMA + 1, 0))
    ]
    if ngramas:
        repetidos = sum(cuantos - 1 for cuantos in Counter(ngramas).values() if cuantos > 1)
        eco = repetidos / len(ngramas)
    else:
        eco = 0.0
    filtro = sum(normalizado.count(marca) for marca in PALABRAS_FILTRO)
    densidad_de_filtro = filtro / max(len(palabras) / 100, 1)
    return round(max(PEOR, MEJOR - eco - densidad_de_filtro / 10), 4)


def _mostrar_vs_contar(frases: list[str]) -> float:
    """Ratio de escena dramatizada frente a resumen.

    El punto ciego declarado se asume: el ratio se calcula con marcas
    superficiales. Un resumen escrito en presente y con dialogo cuenta como
    escena.
    """
    if not frases:
        return PEOR
    sumario = sum(
        1 for frase in frases if any(marca in _norma(frase) for marca in MARCAS_DE_SUMARIO)
    )
    return round((len(frases) - sumario) / len(frases), 4)


def _causalidad(normalizado: str) -> float:
    """«Por tanto / pero» frente a «y entonces».

    El punto ciego declarado se asume: contar conectores detecta el sintoma, no
    la ausencia de cadena causal escrita con buenos conectores.
    """
    causales = sum(normalizado.count(conector) for conector in CONECTORES_CAUSALES)
    aditivos = sum(normalizado.count(conector) for conector in CONECTORES_ADITIVOS)
    if causales + aditivos == 0:
        return MEJOR
    return round(causales / (causales + aditivos), 4)


def _ritmo(frases: list[str]) -> float:
    """Alternancia de densidad y respiro, medida como variacion de longitud.

    El punto ciego declarado se asume: mide la alternancia, no si cae donde la
    estructura la pide. Un patron regular la satisface sin ritmo ninguno.
    """
    longitudes = [len(frase.split()) for frase in frases]
    if len(longitudes) < 2:
        return PEOR
    media = statistics.fmean(longitudes)
    if media == 0:
        return PEOR
    variacion = statistics.pstdev(longitudes) / media
    return round(min(variacion * 2, MEJOR), 4)


def _carga_expositiva(base_terminos: tuple[str, ...], palabras: list[str]) -> float:
    """Densidad de neologismos del mundo sobre el total."""
    if not palabras:
        return MEJOR
    del_mundo = {_norma(termino) for termino in base_terminos}
    expositivos = sum(1 for palabra in palabras if palabra in del_mundo)
    return round(max(PEOR, MEJOR - expositivos / len(palabras)), 4)
