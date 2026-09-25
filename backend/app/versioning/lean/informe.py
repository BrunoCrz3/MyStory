"""De la salida de `lake build` a cuatro veredictos (L-D08, spec 4 § 3.5 y § 3.6).

Lean decide; aquí solo se traduce. Cada `error:` cae en la línea de un teorema, y el índice del
generador dice qué invariante y qué evento comprueba esa línea. Un error que no casa con
ningún teorema —el fichero no compila, la salida cambió de forma— hace fallar las cuatro:
nunca se lee como verde lo que no se entiende.
"""

from __future__ import annotations

import re

from app.process.service import VeredictoGate
from app.versioning.lean.generar import (
    INVARIANTES,
    SCORE,
    Cronologia,
    FicheroLean,
    Invariante,
    Teorema,
)

_ERROR = re.compile(r"error: [^\n]*?Hechos\.lean:(\d+):\d+:")


def lineas_con_error(salida: str) -> list[int]:
    return sorted({int(n) for n in _ERROR.findall(salida)})


def _sin_comprobar(c: Cronologia, invariante: Invariante) -> int:
    """Eventos en los que la invariante es vacuamente cierta por falta de datos."""
    nacimientos = {p.personaje_id for p in c.personajes if p.anio_nacimiento is not None}
    con_exclusion = {x.personaje_id for x in c.excluyentes}
    total = 0
    for e in c.eventos:
        ids = [pr.personaje_id for pr in e.presentes]
        if invariante == "ubicacion":
            vacio = e.lugar_id is None or not ids
        elif invariante == "cronologia":
            vacio = e.anio is None or not any(p in con_exclusion for p in ids)
        elif invariante == "edad":
            vacio = e.anio is None or not any(
                pr.edad is not None and pr.personaje_id in nacimientos for pr in e.presentes
            )
        else:
            vacio = e.anio is None or not any(p in nacimientos for p in ids)
        total += vacio
    return total


def _describir(c: Cronologia, t: Teorema) -> str:
    nombres = {p.personaje_id: p.nombre for p in c.personajes}
    evento = next(e for e in c.eventos if e.evento_id == t.evento_id)
    quien = ", ".join(nombres.get(p, p) for p in t.personajes) or "nadie"
    anio = f", año {evento.anio}" if evento.anio is not None else ""
    descripcion = f"«{evento.descripcion}» " if evento.descripcion else ""
    return (
        f"evento {descripcion}({t.evento_id}) del capítulo {t.numero}, momento {t.momento}"
        f"{anio}, con {quien}"
    )


def veredictos(c: Cronologia, fichero: FicheroLean, salida: str) -> list[VeredictoGate]:
    """Cuatro veredictos de una ejecución que terminó; `salida` es stdout y stderr de Lake."""
    lineas = lineas_con_error(salida)
    ajenas = [n for n in lineas if n not in fichero.indice]
    if ajenas:
        return fallo_total(
            f"error de Lean fuera de los teoremas (líneas {ajenas}): {salida[-800:]}"
        )
    fallidos: dict[Invariante, list[Teorema]] = {i: [] for i in INVARIANTES}
    for n in lineas:
        t = fichero.indice[n]
        fallidos[t.invariante].append(t)
    resultado = []
    total = len(c.eventos)
    for invariante in INVARIANTES:
        malos = fallidos[invariante]
        sin = _sin_comprobar(c, invariante)
        if malos:
            detalle = f"{SCORE[invariante]} falla en " + "; ".join(_describir(c, t) for t in malos)
        else:
            detalle = f"demostrado sobre {total} eventos"
        resultado.append(
            VeredictoGate(
                nombre=SCORE[invariante],
                pasa=not malos,
                valor=0.0 if malos else 1.0,
                detalle=f"{detalle} (sin comprobar: {sin} de {total})",
            )
        )
    return resultado


def fallo_total(motivo: str) -> list[VeredictoGate]:
    """Timeout, toolchain ausente o error de compilación: las cuatro en rojo con su motivo."""
    return [
        VeredictoGate(nombre=SCORE[i], pasa=False, valor=0.0, detalle=motivo) for i in INVARIANTES
    ]
