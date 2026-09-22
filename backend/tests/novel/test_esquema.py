"""H2 · pruebas 2 y 3 — A-20, A-21, A-22.

Las cardinalidades de «Relaciones del dominio» se hacen cumplir con
restricciones, no con codigo: un `unique` lo respeta tambien el script que
alguien corra a mano contra `data/novel.db`, y una comprobacion en el servicio,
no.
"""

import sqlite3

import pytest

from app.commons.db.conexion import Conexion

# Relaciones 1:1 de `definitions.md` y de la spec §7, con la columna que las
# lleva. Las que todavia no tienen tabla —canon, calidad, proceso— se saltan
# solas y entran en cobertura el dia que su hito las cree.
UNO_A_UNO = [
    ("personaje", "arco_id"),  # Personaje recorre Arco
    ("voz", "personaje_id"),  # Personaje tiene Voz
    ("voz_narrativa", "obra_id"),  # la obra tiene un narrador
    ("snapshot_mundo", "escena_id"),  # Escena produce Snapshot (H3)
    ("escena", "brief_id"),  # Brief encarga Escena (H6)
    ("informe_critica", "borrador_id"),  # Informe evalua Borrador (H5)
]


def _tablas(base: Conexion) -> set[str]:
    return {
        fila["name"] for fila in base.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def _columnas_unicas(base: Conexion, tabla: str) -> set[str]:
    """Columnas con unicidad, venga de `UNIQUE`, de un indice o de la clave."""
    unicas = {
        fila["name"] for fila in base.execute(f"PRAGMA table_info({tabla})") if fila["pk"] == 1
    }
    for indice in base.execute(f"PRAGMA index_list({tabla})"):
        if not indice["unique"]:
            continue
        columnas = [f["name"] for f in base.execute(f"PRAGMA index_info({indice['name']})")]
        if len(columnas) == 1:
            unicas.add(columnas[0])
    return unicas


def test_las_cardinalidades_1_1_tienen_restriccion_unique(base: Conexion) -> None:
    existentes = _tablas(base)
    comprobadas = 0
    for tabla, columna in UNO_A_UNO:
        if tabla not in existentes:
            continue
        if columna not in {f["name"] for f in base.execute(f"PRAGMA table_info({tabla})")}:
            continue  # la columna llega con su hito; la tabla ya estaba por otra cosa
        assert columna in _columnas_unicas(base, tabla), f"{tabla}.{columna} no es unica"
        comprobadas += 1
    assert comprobadas >= 3, "H2 tiene que cubrir al menos las tres 1:1 de la Capa 1"


def test_una_segunda_voz_para_el_mismo_personaje_no_entra(base: Conexion) -> None:
    from tests.novel.fabrica import obra_minima

    obra = obra_minima(base)
    base.execute(
        "INSERT INTO voz (personaje_id, lexico) VALUES (?, ?)", (obra.personaje_id, "seco")
    )
    with pytest.raises(sqlite3.IntegrityError):
        base.execute(
            "INSERT INTO voz (personaje_id, lexico) VALUES (?, ?)", (obra.personaje_id, "otro")
        )


def test_evento_escena_es_n_m_con_tabla_puente(base: Conexion) -> None:
    assert "evento_escena" in _tablas(base)

    columnas = {fila["name"]: fila for fila in base.execute("PRAGMA table_info(evento_escena)")}
    assert {"evento_id", "escena_id"} <= set(columnas)
    assert {columnas["evento_id"]["pk"], columnas["escena_id"]["pk"]} == {1, 2}, (
        "la clave primaria del puente es compuesta"
    )

    foraneas = {
        fila["from"]: fila["table"]
        for fila in base.execute("PRAGMA foreign_key_list(evento_escena)")
    }
    assert foraneas == {"evento_id": "evento", "escena_id": "escena"}


def test_un_evento_se_narra_en_varias_escenas_y_una_escena_narra_varios(base: Conexion) -> None:
    from tests.novel.fabrica import obra_minima, otra_escena, un_evento

    obra = obra_minima(base)
    escena_b = otra_escena(base, obra)
    evento_a = un_evento(base, "la caida del puente")
    evento_b = un_evento(base, "el juicio")

    for evento, escena in ((evento_a, obra.escena_id), (evento_a, escena_b), (evento_b, escena_b)):
        base.execute(
            "INSERT INTO evento_escena (evento_id, escena_id) VALUES (?, ?)", (evento, escena)
        )

    escenas_del_evento_a = [
        fila["escena_id"]
        for fila in base.execute(
            "SELECT escena_id FROM evento_escena WHERE evento_id = ? ORDER BY escena_id",
            (evento_a,),
        )
    ]
    eventos_de_la_escena_b = [
        fila["evento_id"]
        for fila in base.execute(
            "SELECT evento_id FROM evento_escena WHERE escena_id = ? ORDER BY evento_id",
            (escena_b,),
        )
    ]
    assert escenas_del_evento_a == sorted([obra.escena_id, escena_b])
    assert eventos_de_la_escena_b == sorted([evento_a, evento_b])


def test_las_claves_foraneas_se_aplican_de_verdad(base: Conexion) -> None:
    """A-20: un `REFERENCES` que no se aplica es documentacion, no integridad."""
    with pytest.raises(sqlite3.IntegrityError):
        base.execute(
            "INSERT INTO parte (obra_id, orden, funcion_dramatica) VALUES (?, ?, ?)",
            (999, 1, "planteamiento"),
        )
