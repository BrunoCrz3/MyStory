"""`longitud` y `nombres_exactos`: los dos validadores programáticos mínimos del hook de
capítulo (filas O-03 y O-02 de `docs/verification.md`)."""

from __future__ import annotations

import re

from app.commons.config import Config
from app.commons.texto import contar_palabras, plano
from app.quality.models import Defecto, ResultadoValidador

_TOKEN = re.compile(r"[^\W\d_]+", re.UNICODE)


def longitud(config: Config, texto: str) -> ResultadoValidador:
    cap = config.umbrales.capitulo
    n = contar_palabras(texto)
    pasa = cap.longitud_min_palabras <= n <= cap.longitud_max_palabras
    detalle = f"{n} palabras; el rango es {cap.longitud_min_palabras}–{cap.longitud_max_palabras}"
    return ResultadoValidador(
        nombre="longitud",
        tipo="programático",
        punto="hook de capítulo",
        pasa=pasa,
        valor=1.0 if pasa else 0.0,
        cierra_el_paso=True,
        detalle=detalle,
        defectos=[]
        if pasa
        else [Defecto(dimension="longitud", gravedad="media", descripcion=detalle)],
    )


def _distancia(a: str, b: str) -> int:
    previa = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        actual = [i]
        for j, cb in enumerate(b, 1):
            actual.append(min(previa[j] + 1, actual[j - 1] + 1, previa[j - 1] + (ca != cb)))
        previa = actual
    return previa[-1]


def _inicio_de_frase(texto: str, posicion: int) -> bool:
    antes = texto[:posicion].rstrip(" \t\"'«“—-")
    return not antes or antes[-1] in ".!?¡¿:\n…"


def nombres_exactos(texto: str, nombres: list[str]) -> ResultadoValidador:
    """Los nombres de la story bible se escriben exactamente igual.

    Caza dos formas de error: la misma palabra con otra grafía (`Tomas` por `Tomás`, `marta`
    por `Marta`) y una palabra capitalizada a una letra de distancia de un nombre (`Martha`
    por `Marta`) que no está al principio de frase, donde una palabra común también va en
    mayúscula. Punto ciego declarado (O-02): un diminutivo legítimo que el brief no declaró
    se marca como error, y un nombre ausente no se detecta.
    """
    formas: dict[str, str] = {}
    for nombre in nombres:
        for parte in _TOKEN.findall(nombre):
            if len(parte) >= 4:
                formas[parte] = plano(parte)
    exactas = set(formas)
    errores: list[str] = []
    for m in _TOKEN.finditer(texto):
        palabra = m.group(0)
        if palabra in exactas or len(palabra) < 4:
            continue
        palabra_plana = plano(palabra)
        for forma, forma_plana in formas.items():
            if palabra_plana == forma_plana:
                errores.append(f"«{palabra}» debería escribirse «{forma}»")
                break
            if (
                palabra[0].isupper()
                and len(forma) >= 5
                and not _inicio_de_frase(texto, m.start())
                and _distancia(palabra_plana, forma_plana) == 1
            ):
                errores.append(f"«{palabra}» se parece a «{forma}» y no es ese nombre")
                break
    unicos = sorted(set(errores))
    detalle = (
        "; ".join(unicos) if unicos else "todos los nombres se escriben como en la story bible"
    )
    return ResultadoValidador(
        nombre="nombres_exactos",
        tipo="programático",
        punto="hook de capítulo",
        pasa=not unicos,
        valor=1.0 if not unicos else 0.0,
        cierra_el_paso=True,
        detalle=detalle,
        defectos=[
            Defecto(dimension="nombres_exactos", gravedad="alta", descripcion=e) for e in unicos
        ],
    )
