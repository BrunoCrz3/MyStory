"""Cola de trabajos y endpoints de generación (RF-PROC-01, 02, 04, 05, RNF-03, RD-06)."""

from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.commons.config import cargar_config
from app.commons.db import conectar
from app.commons.db.migrar import aplicar_migraciones
from app.main import crear_app
from app.process.cola import reclamar
from tests.conftest import Instancia, ValidarContrato
from tests.fixtures.briefs import brief_ejemplo


def _novela(i: Instancia) -> str:
    novel_id: str = i.cliente.post("/novelas", json=brief_ejemplo()).json()["novel_id"]
    return novel_id


def test_lanzar_responde_202_de_inmediato_y_encola(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    novela = _novela(instancia)
    inicio = time.monotonic()
    r = instancia.cliente.post(f"/novelas/{novela}/generaciones")
    assert time.monotonic() - inicio < 1.0
    assert r.status_code == 202
    validar_contra_contrato(r, "lanzarGeneracion")
    cuerpo = r.json()
    assert r.headers["location"] == f"/novelas/{novela}/generaciones/{cuerpo['generacion_id']}"
    assert cuerpo["tipo"] == "inicial"
    assert cuerpo["es_terminal"] is False
    assert cuerpo["intervalo_sondeo_segundos"] >= 1
    assert cuerpo["capitulos_aceptados"] == 0
    assert cuerpo["total_capitulos"] == 10
    assert sum(instancia.modelo.llamadas.values()) == 0


def test_segundo_lanzamiento_da_409_con_el_vivo_y_no_encola(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    novela = _novela(instancia)
    primera = instancia.cliente.post(f"/novelas/{novela}/generaciones").json()
    r = instancia.cliente.post(f"/novelas/{novela}/generaciones")
    assert r.status_code == 409
    validar_contra_contrato(r, "lanzarGeneracion")
    assert r.json()["type"] == "/problemas/generacion-en-curso"
    assert r.json()["generacion_id"] == primera["generacion_id"]
    assert len(instancia.cliente.get(f"/novelas/{novela}/generaciones").json()) == 1


def test_lanzar_sobre_novela_inexistente_da_404(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    r = instancia.cliente.post(f"/novelas/{uuid.uuid4()}/generaciones")
    assert r.status_code == 404
    validar_contra_contrato(r, "lanzarGeneracion")


def test_un_trabajo_que_no_cabe_en_el_pool_falla_al_encolarse(
    validar_contra_contrato: ValidarContrato,
) -> None:
    config = cargar_config()
    umbrales = config.umbrales.model_copy(
        update={"en_vuelo": config.umbrales.en_vuelo.model_copy(update={"total": 1000})}
    )
    estrecha = config.model_copy(update={"umbrales": umbrales})
    with TestClient(crear_app(estrecha)) as c:
        novela = c.post("/novelas", json=brief_ejemplo()).json()["novel_id"]
        r = c.post(f"/novelas/{novela}/generaciones")
        assert r.status_code == 422
        validar_contra_contrato(r, "lanzarGeneracion")
        assert r.json()["type"] == "/problemas/trabajo-no-cabe-en-pool"
        assert c.get(f"/novelas/{novela}/generaciones").json() == []


def test_obtener_y_listar_cumplen_el_contrato(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    novela = _novela(instancia)
    g = instancia.cliente.post(f"/novelas/{novela}/generaciones").json()
    r = instancia.cliente.get(f"/novelas/{novela}/generaciones/{g['generacion_id']}")
    assert r.status_code == 200
    validar_contra_contrato(r, "obtenerGeneracion")
    lista = instancia.cliente.get(f"/novelas/{novela}/generaciones")
    validar_contra_contrato(lista, "listarGeneraciones")
    assert [x["generacion_id"] for x in lista.json()] == [g["generacion_id"]]
    falta = instancia.cliente.get(f"/novelas/{novela}/generaciones/{uuid.uuid4()}")
    assert falta.status_code == 404
    validar_contra_contrato(falta, "obtenerGeneracion")


def test_la_salud_cuenta_los_trabajos_en_cola(instancia: Instancia) -> None:
    novela = _novela(instancia)
    instancia.cliente.post(f"/novelas/{novela}/generaciones")
    assert instancia.cliente.get("/salud").json()["trabajos_en_cola"] == 1


def test_dos_reclamaciones_simultaneas_solo_una_gana(tmp_path: Path) -> None:
    ruta = tmp_path / "cola.db"
    con = conectar(ruta)
    aplicar_migraciones(con)
    con.execute(
        "INSERT INTO obra (novel_id, genero, tono, total_capitulos, creada_en)"
        " VALUES ('n1', 'g', 't', 10, '2026-01-01T00:00:00Z')"
    )
    con.execute(
        "INSERT INTO trabajo (id, novel_id, tipo, estado_cola, estado, version_objetivo,"
        " estimacion, iniciada_en) VALUES ('t1', 'n1', 'inicial', 'pendiente', 'Configurando',"
        " 1, 1000, '2026-01-01T00:00:00Z')"
    )
    con.close()
    ganados: list[str | None] = []
    barrera = threading.Barrier(2)

    def intentar() -> None:
        c: sqlite3.Connection = conectar(ruta)
        try:
            barrera.wait()
            ganados.append(reclamar(c))
        finally:
            c.close()

    hilos = [threading.Thread(target=intentar) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert sorted(ganados, key=str) == [None, "t1"]


def test_es_terminal_solo_en_publicada_y_detenida() -> None:
    from app.process.cola import es_terminal

    assert es_terminal("Publicada") and es_terminal("Detenida")
    for estado in ("Configurando", "Planificando", "Escribiendo", "Validando", "Regenerando"):
        assert not es_terminal(estado)
