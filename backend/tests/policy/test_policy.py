"""Policy engine y audit log de solo escritura (RF-POL-01, RF-POL-02, RF-GUARD-03)."""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.canon.service import HechoPropuesto
from app.commons.config import cargar_config
from app.commons.db import conectar
from app.commons.db.migrar import aplicar_migraciones
from app.guardrail.service import Coincidencia
from app.novel.service import crear_capitulo
from app.policy.service import PolicyEngine, Veredicto, decisiones
from tests.arquitectura.comprobadores import RAIZ_APP, RAIZ_REPO

CONFIG = cargar_config(RAIZ_REPO / "config")


@pytest.fixture
def con(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    c = conectar(tmp_path / "policy.db")
    aplicar_migraciones(c)
    c.execute(
        "INSERT INTO obra (novel_id, genero, tono, total_capitulos, creada_en)"
        " VALUES ('n1', 'g', 't', 10, '2026-01-01T00:00:00Z')"
    )
    yield c
    c.close()


def _veredictos(**fallos: bool) -> list[Veredicto]:
    nombres = ["schema_valido", "palabras_prohibidas", "longitud", "nombres_exactos"]
    return [
        Veredicto(nombre=n, pasa=not fallos.get(n, False), cierra_el_paso=True) for n in nombres
    ]


def test_cada_decision_deja_una_fila_con_regla_entrada_y_resultado(con: sqlite3.Connection) -> None:
    motor = PolicyEngine(CONFIG)
    c1 = crear_capitulo(con, novel_id="n1", numero=1, version=1)
    d = motor.decidir_capitulo(
        con,
        novel_id="n1",
        capitulo_id=c1,
        intentos=0,
        veredictos=_veredictos(),
        reescrituras_por_guardrail=0,
    )
    assert d.accion == "aceptar"
    (fila,) = decisiones(con, novel_id="n1")
    assert fila.regla == "todos-los-validadores-que-cierran-pasan"
    assert fila.resultado == "aceptar"
    assert fila.sujeto_id == c1
    assert json.loads(fila.entrada)["veredictos"]


def test_un_validador_que_falla_devuelve_el_capitulo(con: sqlite3.Connection) -> None:
    motor = PolicyEngine(CONFIG)
    c1 = crear_capitulo(con, novel_id="n1", numero=1, version=1)
    d = motor.decidir_capitulo(
        con,
        novel_id="n1",
        capitulo_id=c1,
        intentos=0,
        veredictos=_veredictos(longitud=True),
        reescrituras_por_guardrail=0,
    )
    assert d.accion == "devolver"
    assert d.fallidos == ["longitud"]


def test_un_validador_que_no_cierra_el_paso_no_devuelve(con: sqlite3.Connection) -> None:
    motor = PolicyEngine(CONFIG)
    c1 = crear_capitulo(con, novel_id="n1", numero=1, version=1)
    veredictos = [*_veredictos(), Veredicto(nombre="ritmo", pasa=False, cierra_el_paso=False)]
    d = motor.decidir_capitulo(
        con,
        novel_id="n1",
        capitulo_id=c1,
        intentos=0,
        veredictos=veredictos,
        reescrituras_por_guardrail=0,
    )
    assert d.accion == "aceptar"


def test_agotar_los_intentos_agota_el_capitulo(con: sqlite3.Connection) -> None:
    motor = PolicyEngine(CONFIG)
    c1 = crear_capitulo(con, novel_id="n1", numero=1, version=1)
    limite = CONFIG.umbrales.orquestacion.max_intentos_capitulo
    d = motor.decidir_capitulo(
        con,
        novel_id="n1",
        capitulo_id=c1,
        intentos=limite,
        veredictos=_veredictos(longitud=True),
        reescrituras_por_guardrail=0,
    )
    assert d.accion == "agotar"
    assert d.detenida_por == "limite-de-intentos-agotado"


def test_dos_pasadas_con_palabra_vetada_detienen(con: sqlite3.Connection) -> None:
    motor = PolicyEngine(CONFIG)
    c1 = crear_capitulo(con, novel_id="n1", numero=1, version=1)
    sublimite = CONFIG.umbrales.guardrail.max_reescrituras
    d = motor.decidir_capitulo(
        con,
        novel_id="n1",
        capitulo_id=c1,
        intentos=1,
        veredictos=_veredictos(palabras_prohibidas=True),
        reescrituras_por_guardrail=sublimite,
    )
    assert d.accion == "detener"
    assert d.detenida_por == "palabra-prohibida-persistente"


def test_hechos_se_adoptan_o_descartan_con_su_regla(con: sqlite3.Connection) -> None:
    motor = PolicyEngine(CONFIG)
    bueno = HechoPropuesto(
        hecho_id="h1",
        enunciado="El barco se llama Alondra",
        tipo="objeto",
        fragmento_soporte="se llamaba Alondra",
    )
    vacio = HechoPropuesto(hecho_id="h2", enunciado="  ", tipo="objeto", fragmento_soporte="x")
    texto = "El barco se llamaba Alondra."
    assert motor.decidir_hecho(con, novel_id="n1", texto=texto, hecho=bueno, conocidos=[])
    assert not motor.decidir_hecho(con, novel_id="n1", texto=texto, hecho=vacio, conocidos=[])
    assert not motor.decidir_hecho(
        con, novel_id="n1", texto=texto, hecho=bueno, conocidos=["el barco se llama alondra"]
    )
    reglas = [(d.sujeto_id, d.regla, d.resultado) for d in decisiones(con, novel_id="n1")]
    assert reglas == [
        ("h1", "fragmento-literal-y-nuevo", "adoptar"),
        ("h2", "enunciado-vacio", "descartar"),
        ("h1", "duplicado-de-hecho-vigente", "descartar"),
    ]


def test_coincidencias_quedan_registradas(con: sqlite3.Connection) -> None:
    motor = PolicyEngine(CONFIG)
    c1 = crear_capitulo(con, novel_id="n1", numero=1, version=1)
    motor.registrar_coincidencias(
        con,
        novel_id="n1",
        capitulo_id=c1,
        intento=1,
        coincidencias=[
            Coincidencia(palabra="Anselmo", nivel="novela", inicio=0, fin=7, fragmento="Anselmo")
        ],
    )
    fila = con.execute("SELECT palabra, nivel, inicio, intento FROM coincidencia").fetchone()
    assert tuple(fila) == ("Anselmo", "novela", 0, 1)
    assert [d.regla for d in decisiones(con, novel_id="n1")] == ["palabra-prohibida"]


def test_el_audit_log_no_se_puede_modificar_ni_borrar(con: sqlite3.Connection) -> None:
    motor = PolicyEngine(CONFIG)
    c1 = crear_capitulo(con, novel_id="n1", numero=1, version=1)
    motor.decidir_capitulo(
        con,
        novel_id="n1",
        capitulo_id=c1,
        intentos=0,
        veredictos=_veredictos(),
        reescrituras_por_guardrail=0,
    )
    with pytest.raises(sqlite3.IntegrityError, match="solo de escritura"):
        con.execute("UPDATE audit_log SET resultado = 'devolver'")
    with pytest.raises(sqlite3.IntegrityError, match="solo de escritura"):
        con.execute("DELETE FROM audit_log")


def test_ningun_sql_del_codigo_modifica_el_audit_log() -> None:
    patron = re.compile(r"(UPDATE\s+audit_log|DELETE\s+FROM\s+audit_log)", re.IGNORECASE)
    for fichero in RAIZ_APP.rglob("*.py"):
        assert not patron.search(fichero.read_text(encoding="utf-8")), fichero
