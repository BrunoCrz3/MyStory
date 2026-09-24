"""`GET /salud`, arranque seguro y cerrojo de instancia (RF-META-01, RNF-12, RF-PROC-03)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.__main__ import argumentos_uvicorn, validar_host
from app.commons.config import cargar_config
from app.commons.db.cerrojo import InstanciaYaEnMarcha
from app.main import crear_app
from tests.arquitectura.comprobadores import RAIZ_REPO
from tests.conftest import ValidarContrato
from tests.dobles.trazador import RegistroTrazas

CONFIG = cargar_config(RAIZ_REPO / "config")


def test_salud_cumple_el_contrato(
    cliente: TestClient, validar_contra_contrato: ValidarContrato
) -> None:
    r = cliente.get("/salud")
    assert r.status_code == 200
    validar_contra_contrato(r, "obtenerSalud")


def test_salud_refleja_la_configuracion_y_el_pool() -> None:
    with TestClient(crear_app(trazador=RegistroTrazas())) as c:
        cuerpo = c.get("/salud").json()
    assert cuerpo["gate_lean_activo"] is CONFIG.umbrales.formal.gate_activo
    assert cuerpo["cerrar_el_paso"] is CONFIG.umbrales.medicion.cerrar_el_paso
    assert cuerpo["tokens_en_vuelo"] == 0
    assert cuerpo["tokens_en_vuelo_total"] == CONFIG.umbrales.en_vuelo.total
    assert cuerpo["version_api"] == "1.1.0"
    assert cuerpo["estado"] == "ok"


def test_sin_langfuse_la_salud_es_degradada() -> None:
    with TestClient(crear_app(trazador=RegistroTrazas(degradado=True))) as c:
        assert c.get("/salud").json()["estado"] == "degradado"


def test_sin_credenciales_de_langfuse_arranca_degradado(cliente: TestClient) -> None:
    assert cliente.get("/salud").json()["estado"] == "degradado"


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_interfaces_locales_permitidas(host: str) -> None:
    validar_host(host, permitir_red=False)


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.10", "::"])
def test_interfaz_no_local_se_rechaza_sin_opcion_explicita(host: str) -> None:
    with pytest.raises(SystemExit, match="interfaz local"):
        validar_host(host, permitir_red=False)
    validar_host(host, permitir_red=True)


def test_el_lanzador_fuerza_un_solo_worker() -> None:
    args = argumentos_uvicorn(["--port", "8123"])
    assert args["workers"] == 1
    assert args["host"] == "127.0.0.1"
    assert args["port"] == 8123


def test_una_segunda_instancia_sobre_la_misma_base_falla() -> None:
    with TestClient(crear_app()), pytest.raises(InstanciaYaEnMarcha), TestClient(crear_app()):
        pass
    # Al cerrar la primera, el cerrojo se libera y otra puede arrancar.
    with TestClient(crear_app()) as c:
        assert c.get("/salud").status_code == 200
