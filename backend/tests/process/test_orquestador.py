"""Orquestador y worker en el `lifespan` (RF-PROC-03, RF-PROC-07, RF-OBS-01, RF-OBS-02)."""

from __future__ import annotations

import time
from typing import Any

from fastapi.testclient import TestClient

from app.commons.config import cargar_config
from app.main import crear_app
from tests.conftest import Instancia
from tests.dobles.guiones import guion_completo
from tests.dobles.modelo import ModeloGuionizado
from tests.dobles.trazador import RegistroTrazas
from tests.fixtures.briefs import brief_ejemplo


def esperar(cliente: TestClient, novela: str, gid: str, condicion: Any, limite: float = 60) -> Any:
    fin = time.monotonic() + limite
    while time.monotonic() < fin:
        g = cliente.get(f"/novelas/{novela}/generaciones/{gid}").json()
        if condicion(g):
            return g
        time.sleep(0.05)
    raise AssertionError(f"la generación no llegó a la condición: {g}")


def _lanzar(i: Instancia) -> tuple[str, str]:
    guion_completo(i.modelo)
    novela = i.cliente.post("/novelas", json=brief_ejemplo()).json()["novel_id"]
    gid = i.cliente.post(f"/novelas/{novela}/generaciones").json()["generacion_id"]
    return novela, gid


def test_una_generacion_escribe_y_acepta_los_diez_capitulos(instancia: Instancia) -> None:
    novela, gid = _lanzar(instancia)
    g = esperar(
        instancia.cliente,
        novela,
        gid,
        lambda g: g["capitulos_aceptados"] == 10 and g["estado"] != "Escribiendo",
    )
    assert g["estado"] in ("Validando", "Publicando", "Publicada")
    capitulos = instancia.cliente.get(f"/novelas/{novela}").json()
    assert capitulos["titulo"] == "El verano del Alondra"
    assert instancia.modelo.llamadas["planificador"] == 1
    assert instancia.modelo.llamadas["redactor"] == 10
    assert instancia.modelo.llamadas["extractor"] == 10


def test_una_sesion_por_novela_y_una_traza_por_generacion(instancia: Instancia) -> None:
    novela, gid = _lanzar(instancia)
    g = esperar(
        instancia.cliente,
        novela,
        gid,
        lambda g: g["capitulos_aceptados"] == 10 and g["estado"] != "Escribiendo",
    )
    trazas = instancia.trazas.trazas
    assert [(t.nombre, t.sesion) for t in trazas] == [("generacion", novela)]
    assert g["traza_langfuse_id"] == trazas[0].traza
    generaciones = instancia.trazas.nombres("generacion")
    assert generaciones.count("planner") == 1
    assert generaciones.count("writer") == 10
    assert generaciones.count("extractor") == 10
    assert all(s.traza == trazas[0].traza for s in instancia.trazas.spans)


def test_el_progreso_se_ve_mientras_escribe(instancia: Instancia) -> None:
    novela, gid = _lanzar(instancia)
    g = esperar(
        instancia.cliente,
        novela,
        gid,
        lambda g: g["capitulos_aceptados"] == 10 and g["estado"] != "Escribiendo",
    )
    assert g["capitulo_actual"] == 10
    assert g["checkpoint"] == 10
    assert g["tokens_consumidos"] > 0
    assert g["coste_usd"] > 0


def test_al_cerrar_el_lifespan_el_worker_termina() -> None:
    config = cargar_config()
    modelo = ModeloGuionizado(config)
    app = crear_app(config, cliente_modelo=modelo, trazador=RegistroTrazas())
    with TestClient(app):
        worker = app.state.worker
        assert worker.vivo
    assert not worker.vivo
