"""Validadores del gate de publicación (RF-QUA-03, D-17). No llaman al modelo.

F1 corre `estructura_edicion` y `elementos_obligatorios`. F2 añade `cierre_arco` en su mitad
programática (D-15): ninguna promesa puede seguir pendiente al cerrar el último capítulo; la
mitad semántica es el criterio «arco» del judge, que puntúa cada capítulo y, con la medición
cerrada, suspende el último antes de que llegue aquí. F4 añade `regeneracion_fiel` desde la
segunda versión.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.canon import service as canon
from app.commons.config import Config
from app.novel import service as novel
from app.process.service import VeredictoGate
from app.versioning import repository
from app.versioning.huella import contenido, hash_contenido


def estructura_edicion(
    con: sqlite3.Connection, *, novel_id: str, capitulos: list[dict[str, Any]]
) -> VeredictoGate:
    """O-57 y O-58: exactamente `obra.capitulos` capítulos, con títulos únicos y no vacíos."""
    total = novel.total_capitulos(con, novel_id=novel_id)
    problemas = []
    numeros = sorted(int(c["numero"]) for c in capitulos)
    if numeros != list(range(1, total + 1)):
        problemas.append(f"hay {len(numeros)} capítulos aceptados y la obra tiene {total}")
    titulos = [(c["titulo"] or "").strip() for c in capitulos]
    vacios = sorted(int(c["numero"]) for c, t in zip(capitulos, titulos, strict=True) if not t)
    if vacios:
        problemas.append(f"capítulos sin título: {vacios}")
    repetidos = sorted({t for t in titulos if t and titulos.count(t) > 1})
    if repetidos:
        problemas.append(f"títulos repetidos: {repetidos}")
    return VeredictoGate(
        nombre="estructura_edicion",
        pasa=not problemas,
        valor=0.0 if problemas else 1.0,
        detalle="; ".join(problemas) or "estructura correcta",
    )


def elementos_obligatorios(
    con: sqlite3.Connection, *, novel_id: str, ids: list[str]
) -> VeredictoGate:
    """O-04: todo elemento obligatorio aparece en al menos un capítulo de la versión."""
    ausentes = repository.obligatorios_ausentes(con, novel_id=novel_id, capitulos=ids)
    return VeredictoGate(
        nombre="elementos_obligatorios",
        pasa=not ausentes,
        valor=0.0 if ausentes else 1.0,
        detalle=f"obligatorios sin capítulo: {ausentes}" if ausentes else "todos presentes",
    )


def cierre_arco(
    config: Config, con: sqlite3.Connection, *, novel_id: str, version: int, ids: list[str]
) -> VeredictoGate:
    """O-34, O-35: al cerrar la novela no queda ninguna promesa pendiente («sin final
    abrupto»). Cuenta hasta `continuidad.promesas_pendientes_al_cerrar`, que es cero."""
    pendientes = canon.promesas_pendientes_al_cierre(
        con, novel_id=novel_id, version=version, capitulo_ids=ids
    )
    maximo = config.umbrales.continuidad.promesas_pendientes_al_cerrar
    pasa = len(pendientes) <= maximo
    return VeredictoGate(
        nombre="cierre_arco",
        pasa=pasa,
        valor=1.0 if pasa else 0.0,
        detalle="ninguna promesa pendiente al cerrar"
        if not pendientes
        else "promesas pendientes al cerrar: " + "; ".join(p.enunciado for p in pendientes),
    )


def regeneracion_fiel(
    con: sqlite3.Connection, *, novel_id: str, version: int, candidatos: dict[int, str]
) -> VeredictoGate:
    """O-61…O-64: la versión nueva cambia **exactamente** los capítulos que la anterior
    marcó `Obsoleto`, y la anterior sigue consultable con su hash intacto (regla 15)."""
    problemas: list[str] = []
    anterior = repository.leer_version(con, novel_id=novel_id, version=version - 1)
    if anterior is None:
        problemas.append(f"la versión {version - 1} no es consultable")
    else:
        previos = repository.vinculos(con, novel_id=novel_id, version=version - 1)
        ids = list(previos.values())
        recalculado = hash_contenido(anterior["titulo"], contenido(con, novel_id=novel_id, ids=ids))
        if recalculado != anterior["hash"]:
            problemas.append(f"el hash de la versión {version - 1} ya no cuadra")
        estados = repository.estados_de_capitulos(con, novel_id=novel_id, ids=ids)
        obsoletos = {n for n, cid in previos.items() if estados.get(cid) == "Obsoleto"}
        cambiados = {n for n in candidatos if candidatos[n] != previos.get(n)}
        if sorted(candidatos) != sorted(previos):
            problemas.append("la versión nueva no tiene los mismos capítulos que la anterior")
        if infieles := sorted(cambiados - obsoletos):
            problemas.append(f"cambian capítulos no afectados: {infieles}")
        if pendientes := sorted(obsoletos - cambiados):
            problemas.append(f"capítulos obsoletos sin reescribir: {pendientes}")
    return VeredictoGate(
        nombre="regeneracion_fiel",
        pasa=not problemas,
        valor=0.0 if problemas else 1.0,
        detalle="; ".join(problemas) or "solo cambian los capítulos afectados",
    )
