"""SQL de los informes de crítica, sus defectos y sus scores. Solo inserta y lee."""

from __future__ import annotations

import sqlite3
import uuid

from app.quality.models import Defecto, InformeCritica, ResultadoValidador, Score


def insertar_informe(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    capitulo_id: str,
    intento: int,
    decision: str,
    creado_en: str,
    resultados: list[ResultadoValidador],
) -> str:
    informe_id = str(uuid.uuid4())
    con.execute(
        "INSERT INTO informe_critica (id, novel_id, capitulo_id, intento, decision, creado_en)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (informe_id, novel_id, capitulo_id, intento, decision, creado_en),
    )
    defectos = [(r.nombre, d) for r in resultados for d in r.defectos]
    con.executemany(
        "INSERT INTO defecto (id, novel_id, informe_id, orden, validador, dimension, gravedad,"
        " descripcion, localizacion, clasificacion) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                str(uuid.uuid4()),
                novel_id,
                informe_id,
                orden,
                validador,
                d.dimension,
                d.gravedad,
                d.descripcion,
                d.localizacion,
                d.clasificacion,
            )
            for orden, (validador, d) in enumerate(defectos)
        ],
    )
    con.executemany(
        "INSERT INTO score (id, novel_id, informe_id, orden, validador, valor, pasa,"
        " cierra_el_paso, detalle) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                str(uuid.uuid4()),
                novel_id,
                informe_id,
                orden,
                r.nombre,
                r.valor,
                int(r.pasa),
                int(r.cierra_el_paso),
                r.detalle,
            )
            for orden, r in enumerate(resultados)
        ],
    )
    return informe_id


def informes_de_capitulo(
    con: sqlite3.Connection, *, novel_id: str, capitulo_id: str
) -> list[InformeCritica]:
    informes = con.execute(
        "SELECT id, capitulo_id, intento, decision, creado_en FROM informe_critica"
        " WHERE novel_id = ? AND capitulo_id = ? ORDER BY intento, rowid",
        (novel_id, capitulo_id),
    ).fetchall()
    resultado = []
    for i in informes:
        defectos = con.execute(
            "SELECT dimension, gravedad, descripcion, localizacion, clasificacion FROM defecto"
            " WHERE novel_id = ? AND informe_id = ? ORDER BY orden",
            (novel_id, i["id"]),
        ).fetchall()
        scores = con.execute(
            "SELECT validador, valor, pasa, cierra_el_paso, detalle FROM score"
            " WHERE novel_id = ? AND informe_id = ? ORDER BY orden",
            (novel_id, i["id"]),
        ).fetchall()
        resultado.append(
            InformeCritica(
                informe_id=i["id"],
                capitulo_id=i["capitulo_id"],
                intento=i["intento"],
                decision=i["decision"],
                creado_en=i["creado_en"],
                defectos=[Defecto(**dict(d)) for d in defectos],
                scores=[
                    Score(
                        validador=s["validador"],
                        valor=s["valor"],
                        pasa=bool(s["pasa"]),
                        cierra_el_paso=bool(s["cierra_el_paso"]),
                        detalle=s["detalle"],
                    )
                    for s in scores
                ],
            )
        )
    return resultado
