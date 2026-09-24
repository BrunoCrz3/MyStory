"""El grabador de casetes no escribe la autenticación y el reproductor devuelve lo grabado."""

from __future__ import annotations

import json
from pathlib import Path

import httpx2
import pytest

from tests.arquitectura.secretos import violaciones_secretos
from tests.herramientas.casetes import TransporteGrabador, reproductor


def _servidor(request: httpx2.Request) -> httpx2.Response:
    return httpx2.Response(
        200,
        headers={"content-type": "application/json", "set-cookie": "sesion=abc"},
        json={"eco": json.loads(request.content)},
    )


@pytest.mark.anyio
async def test_graba_sin_cabeceras_de_autenticacion_y_reproduce(tmp_path: Path) -> None:
    casete = tmp_path / "casetes" / "prueba.json"
    grabador = TransporteGrabador(httpx2.MockTransport(_servidor), casete)
    async with httpx2.AsyncClient(transport=grabador, base_url="https://api.ejemplo") as c:
        r = await c.post(
            "/v1/messages",
            json={"hola": "mundo"},
            headers={"x-api-key": "secreto", "authorization": "Bearer secreto"},
        )
    assert r.json() == {"eco": {"hola": "mundo"}}

    texto = casete.read_text(encoding="utf-8")
    assert "secreto" not in texto and "sesion=abc" not in texto
    assert violaciones_secretos([casete], casete.parent, set()) == []
    [grabada] = json.loads(texto)
    assert grabada["peticion"]["ruta"] == "/v1/messages"
    assert grabada["peticion"]["cuerpo"] == {"hola": "mundo"}

    async with httpx2.AsyncClient(
        transport=reproductor(casete), base_url="https://api.ejemplo"
    ) as c:
        r = await c.post("/v1/messages", json={"hola": "mundo"})
        assert r.status_code == 200 and r.json() == {"eco": {"hola": "mundo"}}
        with pytest.raises(AssertionError, match="no grabada"):
            await c.post("/v1/messages", json={})


@pytest.mark.anyio
async def test_el_reproductor_rechaza_una_peticion_distinta(tmp_path: Path) -> None:
    casete = tmp_path / "c.json"
    casete.write_text(
        json.dumps(
            [
                {
                    "peticion": {"metodo": "POST", "ruta": "/v1/messages", "cabeceras": {}},
                    "respuesta": {"estado": 200, "cabeceras": {}, "cuerpo": {}},
                }
            ]
        ),
        encoding="utf-8",
    )
    async with httpx2.AsyncClient(transport=reproductor(casete), base_url="https://x") as c:
        with pytest.raises(AssertionError, match="se esperaba POST /v1/messages"):
            await c.post("/v1/messages/count_tokens", json={})
