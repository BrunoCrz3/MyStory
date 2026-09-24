"""La aplicación arranca con su `lifespan` y responde. Es el invariante global del plan (§ 0.1)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_la_app_arranca_y_responde(app: FastAPI) -> None:
    with TestClient(app) as cliente:
        assert cliente.get("/salud").status_code == 200
