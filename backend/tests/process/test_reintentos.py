"""Reintentos con límite, dos contadores separados y topes por novela
(RF-PROC-08, RF-PROC-09, RNF-04, RNF-13, RF-OBS-04)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.commons.config import Config, cargar_config
from app.commons.llm import FalloInfraestructura, Mensaje, Peticion
from app.commons.llm.llamar import Consumo, LlamadorModelo, acumular_en
from app.commons.llm.pool import PoolEnVuelo
from app.main import crear_app
from tests.dobles.guiones import guion_completo, redactar
from tests.dobles.modelo import ModeloGuionizado
from tests.dobles.trazador import RegistroTrazas
from tests.fixtures.briefs import brief_ejemplo
from tests.process.test_orquestador import esperar

CONFIG = cargar_config()


def _config(**orquestacion: Any) -> Config:
    u = CONFIG.umbrales
    backoff = u.orquestacion.backoff.model_copy(update={"base_segundos": 0.0})
    nueva = u.orquestacion.model_copy(update={"backoff": backoff, **orquestacion})
    return CONFIG.model_copy(update={"umbrales": u.model_copy(update={"orquestacion": nueva})})


def _con_coste(**coste: Any) -> Config:
    base = _config()
    u = base.umbrales
    return base.model_copy(
        update={"umbrales": u.model_copy(update={"coste": u.coste.model_copy(update=coste)})}
    )


def _peticion() -> Peticion:
    return Peticion(
        rol="redactor",
        system="s",
        mensajes=[Mensaje(role="user", contenido="x")],
        prompt="writer",
        hash_prompt="h",
    )


@pytest.mark.anyio
async def test_el_retroceso_es_exponencial_con_jitter_y_tiene_limite() -> None:
    esperas: list[float] = []

    async def dormir(s: float) -> None:
        esperas.append(s)

    modelo = ModeloGuionizado(
        CONFIG,
        salidas={
            "redactor": [
                FalloInfraestructura("429"),
                FalloInfraestructura("503"),
                "ok",
            ]
        },
    )
    llamador = LlamadorModelo(
        CONFIG, modelo, PoolEnVuelo(10**6), RegistroTrazas(), dormir=dormir, azar=lambda: 0.5
    )
    consumo = Consumo()
    with acumular_en(consumo):
        respuesta = await llamador.llamar(_peticion())
    assert respuesta.texto == "ok"
    b = CONFIG.umbrales.orquestacion.backoff
    assert esperas == [b.base_segundos * (1 + 0.5), b.base_segundos * b.factor * (1 + 0.5)]
    assert consumo.reintentos_infra == 2


@pytest.mark.anyio
async def test_agotar_los_reintentos_de_infraestructura_lanza() -> None:
    limite = CONFIG.umbrales.orquestacion.max_intentos_trabajo
    modelo = ModeloGuionizado(CONFIG, salidas={"redactor": [FalloInfraestructura("429")] * 10})

    async def dormir(s: float) -> None:
        return None

    llamador = LlamadorModelo(CONFIG, modelo, PoolEnVuelo(10**6), RegistroTrazas(), dormir=dormir)
    with pytest.raises(FalloInfraestructura):
        await llamador.llamar(_peticion())
    # Tres reintentos después de la primera llamada: el peor caso de thresholds.yaml (2+4+8 s).
    assert modelo.llamadas["redactor"] == limite + 1


def _ejecutar(config: Config, preparar: Any) -> tuple[dict[str, Any], ModeloGuionizado, TestClient]:
    modelo = ModeloGuionizado(config)
    guion_completo(modelo)
    preparar(modelo)
    trazas = RegistroTrazas()
    cliente = TestClient(crear_app(config, cliente_modelo=modelo, trazador=trazas))
    cliente.__enter__()
    novela = cliente.post("/novelas", json=brief_ejemplo()).json()["novel_id"]
    gid = cliente.post(f"/novelas/{novela}/generaciones").json()["generacion_id"]
    g = esperar(
        cliente,
        novela,
        gid,
        lambda g: (
            g["estado"] in ("Detenida", "Validando", "Publicada") and g["terminada_en"] is not None
        ),
    )
    return g, modelo, cliente


def test_un_429_se_reintenta_sin_gastar_intentos_del_capitulo() -> None:
    def preparar(m: ModeloGuionizado) -> None:
        m.encolar("redactor", FalloInfraestructura("429"), redactar)

    g, _, cliente = _ejecutar(_config(), preparar)
    try:
        novela = g["novel_id"]
        r = cliente.get(f"/novelas/{novela}/generaciones/{g['generacion_id']}").json()
        assert r["capitulos_aceptados"] == 10
        intentos = [
            f["intentos"]
            for f in cliente.app.state.recursos.db.ejecutar_sync(  # type: ignore[attr-defined]
                lambda con: con.execute(
                    "SELECT intentos FROM capitulo WHERE novel_id = ? ORDER BY numero", (novela,)
                ).fetchall()
            )
        ]
        assert intentos == [0] * 10
    finally:
        cliente.__exit__(None, None, None)


def test_agotar_los_reintentos_de_infraestructura_detiene_e_informa() -> None:
    def preparar(m: ModeloGuionizado) -> None:
        m.encolar("redactor", *[FalloInfraestructura("503")] * 10)

    g, _, cliente = _ejecutar(_config(), preparar)
    try:
        assert g["estado"] == "Detenida"
        assert g["detenida_por"] == "error-interno"
        assert g["es_terminal"] is True
    finally:
        cliente.__exit__(None, None, None)


def test_un_capitulo_que_no_converge_detiene_con_limite_agotado() -> None:
    from tests.fixtures.borradores import borrador

    def preparar(m: ModeloGuionizado) -> None:
        m.encolar("redactor", *[borrador(200)] * 10)

    g, _, cliente = _ejecutar(_config(), preparar)
    try:
        assert g["estado"] == "Detenida"
        assert g["detenida_por"] == "limite-de-intentos-agotado"
        assert g["capitulo_actual"] == 1
        assert g["intentos_capitulo_actual"] == CONFIG.umbrales.orquestacion.max_intentos_capitulo
    finally:
        cliente.__exit__(None, None, None)


def test_superar_el_coste_maximo_detiene() -> None:
    g, _, cliente = _ejecutar(_con_coste(coste_maximo_novela=0.000001), lambda m: None)
    try:
        assert g["estado"] == "Detenida"
        assert g["detenida_por"] == "error-interno"
        assert g["capitulos_aceptados"] < 10
    finally:
        cliente.__exit__(None, None, None)


def test_superar_la_latencia_maxima_detiene() -> None:
    g, _, cliente = _ejecutar(_con_coste(latencia_maxima_novela=0.0), lambda m: None)
    try:
        assert g["estado"] == "Detenida"
    finally:
        cliente.__exit__(None, None, None)


def test_tokens_y_coste_de_la_generacion_son_la_suma_de_sus_llamadas() -> None:
    config = _config()
    modelo = ModeloGuionizado(config)
    guion_completo(modelo)
    trazas = RegistroTrazas()
    with TestClient(crear_app(config, cliente_modelo=modelo, trazador=trazas)) as cliente:
        novela = cliente.post("/novelas", json=brief_ejemplo()).json()["novel_id"]
        gid = cliente.post(f"/novelas/{novela}/generaciones").json()["generacion_id"]
        g = esperar(cliente, novela, gid, lambda g: g["terminada_en"] is not None)
    llamadas = [s for s in trazas.spans if s.tipo == "generacion"]
    assert g["tokens_consumidos"] == sum(
        (s.tokens_entrada or 0) + (s.tokens_salida or 0) for s in llamadas
    )
    assert g["coste_usd"] == pytest.approx(sum(s.coste_usd or 0 for s in llamadas), abs=1e-5)
