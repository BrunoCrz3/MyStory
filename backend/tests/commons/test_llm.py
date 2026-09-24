"""Cliente del modelo: conteo previo, petición por rol y clasificación del fallo (P06).

La implementación de producción corre contra `httpx2.MockTransport`: se prueba la
serialización real del SDK sin llamar al proveedor (TO-034, capa 2).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx2
import pytest

from app.commons.config import cargar_config
from app.commons.llm import (
    ClienteAnthropic,
    ClienteModelo,
    ErrorModelo,
    FalloInfraestructura,
    Mensaje,
    Peticion,
    Recuento,
    SalidaTruncada,
)
from tests.arquitectura.comprobadores import RAIZ_REPO
from tests.dobles.modelo import ModeloGuionizado

CONFIG = cargar_config(RAIZ_REPO / "config")
ESQUEMA = {
    "type": "object",
    "properties": {"titulo": {"type": "string"}},
    "required": ["titulo"],
    "additionalProperties": False,
}


def _peticion(system: str = "Eres el planificador.") -> Peticion:
    return Peticion(
        rol="planificador",
        system=system,
        mensajes=[Mensaje(role="user", contenido="Planifica.")],
        esquema_salida=ESQUEMA,
        prompt="planner",
        hash_prompt="abc123",
    )


def _mensaje(texto: str, stop: str = "end_turn") -> dict[str, Any]:
    return {
        "id": "msg_01",
        "type": "message",
        "role": "assistant",
        "model": CONFIG.modelos.roles.planificador.id,
        "content": [{"type": "text", "text": texto}],
        "stop_reason": stop,
        "stop_sequence": None,
        "usage": {
            "input_tokens": 1000,
            "output_tokens": 500,
            "output_tokens_details": {"thinking_tokens": 200},
        },
    }


Manejador = Callable[[httpx2.Request], httpx2.Response]


def _cliente(manejador: Manejador) -> tuple[ClienteAnthropic, list[httpx2.Request]]:
    peticiones: list[httpx2.Request] = []

    def registrar(request: httpx2.Request) -> httpx2.Response:
        peticiones.append(request)
        return manejador(request)

    http = httpx2.AsyncClient(transport=httpx2.MockTransport(registrar))
    return ClienteAnthropic(CONFIG, api_key="clave-de-prueba", http_client=http), peticiones


def _ok(request: httpx2.Request) -> httpx2.Response:
    if request.url.path.endswith("/count_tokens"):
        return httpx2.Response(200, json={"input_tokens": 1234})
    return httpx2.Response(200, json=_mensaje('{"titulo": "El verano del Alondra"}'))


@pytest.mark.anyio
async def test_la_peticion_lleva_modelo_effort_y_max_tokens_del_rol() -> None:
    cliente, peticiones = _cliente(_ok)
    p = _peticion()
    recuento = await cliente.contar_tokens(p)
    assert recuento.tokens_entrada == 1234
    respuesta = await cliente.generar(p, recuento)

    cuerpo = json.loads(peticiones[-1].content)
    rol = CONFIG.modelos.roles.planificador
    assert cuerpo["model"] == rol.id
    assert cuerpo["max_tokens"] == CONFIG.max_tokens("planificador")
    assert cuerpo["output_config"]["effort"] == rol.effort
    assert cuerpo["output_config"]["format"]["schema"] == ESQUEMA
    assert cuerpo["system"] == "Eres el planificador."
    assert "thinking" not in cuerpo or cuerpo["thinking"]["type"] == "adaptive"
    assert respuesta.datos == {"titulo": "El verano del Alondra"}


@pytest.mark.anyio
async def test_el_timeout_esta_fijado_y_no_hay_reintentos_del_sdk() -> None:
    cliente, _ = _cliente(_ok)
    assert cliente.timeout_segundos == CONFIG.umbrales.orquestacion.timeout_llamada_segundos
    assert cliente.sdk.max_retries == 0


@pytest.mark.anyio
async def test_uso_se_traduce_a_tokens_y_coste() -> None:
    cliente, _ = _cliente(_ok)
    p = _peticion()
    r = await cliente.generar(p, await cliente.contar_tokens(p))
    precio = CONFIG.umbrales.coste.precio_usd_por_millon[CONFIG.modelos.roles.planificador.id]
    assert r.tokens_entrada == 1000
    assert r.tokens_salida == 500
    assert r.tokens_razonamiento == 200
    assert r.coste_usd == pytest.approx((1000 * precio.entrada + 500 * precio.salida) / 1e6)


@pytest.mark.anyio
async def test_generar_con_recuento_de_otra_peticion_lanza() -> None:
    cliente, _ = _cliente(_ok)
    recuento = await cliente.contar_tokens(_peticion())
    otra = _peticion(system="distinta")
    with pytest.raises(ValueError, match="recuento"):
        await cliente.generar(otra, recuento)


@pytest.mark.anyio
@pytest.mark.parametrize("codigo", [429, 500, 503, 529])
async def test_fallos_de_infraestructura(codigo: int) -> None:
    def manejador(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/count_tokens"):
            return httpx2.Response(200, json={"input_tokens": 10})
        return httpx2.Response(
            codigo, json={"type": "error", "error": {"type": "x", "message": "x"}}
        )

    cliente, _ = _cliente(manejador)
    p = _peticion()
    with pytest.raises(FalloInfraestructura):
        await cliente.generar(p, await cliente.contar_tokens(p))


@pytest.mark.anyio
async def test_timeout_es_fallo_de_infraestructura() -> None:
    def manejador(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("lento", request=request)

    cliente, _ = _cliente(manejador)
    with pytest.raises(FalloInfraestructura):
        await cliente.contar_tokens(_peticion())


@pytest.mark.anyio
async def test_un_400_no_es_de_infraestructura() -> None:
    def manejador(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            400, json={"type": "error", "error": {"type": "invalid_request_error", "message": "x"}}
        )

    cliente, _ = _cliente(manejador)
    with pytest.raises(ErrorModelo) as info:
        await cliente.contar_tokens(_peticion())
    assert not isinstance(info.value, FalloInfraestructura)


@pytest.mark.anyio
async def test_salida_truncada_por_max_tokens() -> None:
    def manejador(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/count_tokens"):
            return httpx2.Response(200, json={"input_tokens": 10})
        return httpx2.Response(200, json=_mensaje('{"titulo": "El ver', stop="max_tokens"))

    cliente, _ = _cliente(manejador)
    p = _peticion()
    with pytest.raises(SalidaTruncada):
        await cliente.generar(p, await cliente.contar_tokens(p))


def test_recuento_se_ata_a_la_peticion() -> None:
    p = _peticion()
    recuento = Recuento.de(p, tokens_entrada=10, max_tokens=100)
    assert recuento.corresponde_a(p)
    assert not recuento.corresponde_a(_peticion(system="otra"))


@pytest.mark.anyio
async def test_el_doble_cumple_el_protocolo() -> None:
    doble: ClienteModelo = ModeloGuionizado(CONFIG, salidas={"planificador": [{"titulo": "T"}]})
    p = _peticion()
    r = await doble.generar(p, await doble.contar_tokens(p))
    assert r.datos == {"titulo": "T"}
