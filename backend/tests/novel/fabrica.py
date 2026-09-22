"""Obra minima de prueba. Datos reales contra la base real: nada de mocks."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import count

from app.commons.db.conexion import Conexion

_orden = count(1)


@dataclass(frozen=True)
class ObraDePrueba:
    obra_id: int
    parte_id: int
    capitulo_id: int
    escena_id: int
    personaje_id: int
    lugar_id: int


def obra_minima(base: Conexion) -> ObraDePrueba:
    obra_id = _insertar(
        base,
        "INSERT INTO obra (id, premisa, genero, extension_objetivo, publico) VALUES (1,?,?,?,?)",
        ("Un puente que recuerda", "ciencia ficcion", 90000, "adulto"),
    )
    parte_id = _insertar(
        base,
        "INSERT INTO parte (obra_id, orden, funcion_dramatica, punto_de_giro) VALUES (?,?,?,?)",
        (obra_id, next(_orden), "planteamiento", "el puente habla"),
    )
    capitulo_id = _insertar(
        base,
        "INSERT INTO capitulo (parte_id, orden, gancho_de_cierre) VALUES (?,?,?)",
        (parte_id, next(_orden), "la voz se repite"),
    )
    personaje_id = _insertar(
        base,
        "INSERT INTO personaje (nombre, deseo, necesidad, herida, rol_narrativo) "
        "VALUES (?,?,?,?,?)",
        ("Ilia", "cruzar", "confiar", "el derrumbe", "protagonista"),
    )
    lugar_id = _insertar(
        base,
        "INSERT INTO lugar (nombre, geografia, atmosfera_sensorial) VALUES (?,?,?)",
        ("El vado", "garganta fluvial", "olor a hierro mojado"),
    )
    escena_id = _insertar(
        base,
        "INSERT INTO escena (capitulo_id, orden, objetivo, personaje_pov_id, lugar_id) "
        "VALUES (?,?,?,?,?)",
        (capitulo_id, next(_orden), "llegar al otro lado", personaje_id, lugar_id),
    )
    return ObraDePrueba(obra_id, parte_id, capitulo_id, escena_id, personaje_id, lugar_id)


def otra_escena(base: Conexion, obra: ObraDePrueba) -> int:
    return _insertar(
        base,
        "INSERT INTO escena (capitulo_id, orden, objetivo) VALUES (?,?,?)",
        (obra.capitulo_id, next(_orden), "seguir"),
    )


def un_evento(base: Conexion, que_ocurre: str) -> int:
    return _insertar(
        base,
        "INSERT INTO evento (que_ocurre, momento_en_la_fabula) VALUES (?,?)",
        (que_ocurre, "ano 12 del vado"),
    )


def _insertar(base: Conexion, sql: str, parametros: tuple[object, ...]) -> int:
    cursor = base.execute(sql, parametros)
    identificador = cursor.lastrowid
    assert identificador is not None
    return identificador
