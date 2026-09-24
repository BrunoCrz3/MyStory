"""Cierre de F1: una novela de diez capítulos por HTTP y reanudación tras matar el proceso.

Las dos pruebas levantan el backend como proceso real (`tests/e2e/app_con_dobles.py`), con el
modelo y el trazador dobles: lo que se prueba es el camino HTTP, el worker del `lifespan` y
la base en disco, no el proveedor.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx2
import jsonschema

from tests.contrato.normalizar import cargar_contrato, schema_de_respuesta
from tests.e2e.proceso import backend, entorno
from tests.fixtures.briefs import brief_ejemplo

APP_CON_DOBLES = ["-m", "tests.e2e.app_con_dobles"]
_CONTRATO = cargar_contrato()


def _conforme(r: httpx2.Response, operacion: str) -> Any:
    tipo = r.headers["content-type"].split(";")[0]
    schema = schema_de_respuesta(_CONTRATO, operacion, r.status_code, tipo)
    assert schema is not None, f"{operacion} no declara {r.status_code} {tipo}"
    jsonschema.validate(r.json(), schema)
    return r.json()


def _sondear(
    base: str, novela: str, gid: str, condicion: Callable[[dict[str, Any]], bool], limite: float
) -> dict[str, Any]:
    fin = time.monotonic() + limite
    while True:
        r = httpx2.get(f"{base}/novelas/{novela}/generaciones/{gid}", timeout=5)
        g: dict[str, Any] = _conforme(r, "obtenerGeneracion")
        if condicion(g):
            return g
        if time.monotonic() > fin:
            raise AssertionError(f"la generación no llegó a la condición en {limite} s: {g}")
        time.sleep(0.05)


def _lanzar(base: str) -> tuple[str, str]:
    r = httpx2.post(f"{base}/novelas", json=brief_ejemplo(), timeout=10)
    assert r.status_code == 201
    novela = _conforme(r, "crearNovela")["novel_id"]
    r = httpx2.post(f"{base}/novelas/{novela}/generaciones", timeout=10)
    assert r.status_code == 202
    return novela, _conforme(r, "lanzarGeneracion")["generacion_id"]


def _aceptados(db: Path) -> list[tuple[int, str, str, str]]:
    with sqlite3.connect(db) as con:
        filas = con.execute(
            "SELECT numero, id, aceptado_en, texto FROM capitulo "
            "WHERE estado = 'Aceptado' ORDER BY numero"
        ).fetchall()
    return [(int(n), str(i), str(a), str(t)) for n, i, a, t in filas]


def test_una_novela_de_diez_capitulos_se_publica_por_http(tmp_path: Path) -> None:
    with backend(entorno(tmp_path / "f1.db"), modulo=APP_CON_DOBLES) as (base, _):
        novela, gid = _lanzar(base)
        g = _sondear(base, novela, gid, lambda g: g["es_terminal"], limite=120)
        assert g["estado"] == "Publicada", g
        assert g["version_resultante"] == 1 and g["checkpoint"] == 10

        obra = _conforme(httpx2.get(f"{base}/novelas/{novela}", timeout=5), "obtenerNovela")
        assert obra["estado"] == "Publicada" and obra["version_vigente"] == 1
        versiones = _conforme(
            httpx2.get(f"{base}/novelas/{novela}/versiones", timeout=5), "listarVersiones"
        )
        assert [v["version"] for v in versiones] == [1]
        capitulos = _conforme(
            httpx2.get(f"{base}/novelas/{novela}/versiones/1/capitulos", timeout=5),
            "listarCapitulos",
        )
        assert [c["numero"] for c in capitulos] == list(range(1, 11))
        assert all(c["estado"] == "Aceptado" and c["texto"] for c in capitulos)


def test_matar_el_proceso_a_mitad_y_rearrancar_acaba_publicada_sin_reescribir(
    tmp_path: Path,
) -> None:
    db = tmp_path / "f1.db"
    env = entorno(db, STORYMAKER_E2E_RETARDO_S="0.15")

    with backend(env, modulo=APP_CON_DOBLES) as (base, proceso):
        novela, gid = _lanzar(base)
        _sondear(base, novela, gid, lambda g: g["capitulo_actual"] == 5, limite=120)
        proceso.kill()
        proceso.wait(timeout=10)

    antes = _aceptados(db)
    assert [n for n, *_ in antes][:4] == [1, 2, 3, 4]

    with backend(entorno(db), modulo=APP_CON_DOBLES) as (base, _):
        g = _sondear(base, novela, gid, lambda g: g["es_terminal"], limite=120)
        assert g["estado"] == "Publicada", g
        assert g["generacion_id"] == gid and g["version_resultante"] == 1

    despues = _aceptados(db)
    assert [n for n, *_ in despues] == list(range(1, 11)), "ninguno se aceptó dos veces"
    # Los aceptados antes del corte son la misma fila: mismo id, misma hora, mismo texto.
    assert despues[: len(antes)] == antes
    with sqlite3.connect(db) as con:
        [(trabajos,)] = con.execute("SELECT COUNT(*) FROM trabajo").fetchall()
    assert trabajos == 1
