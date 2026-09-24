"""La aplicación arranca con su `lifespan`. Es el invariante global del plan (§ 0.1)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_la_app_arranca(app: FastAPI) -> None:
    with TestClient(app) as cliente:
        assert cliente.app is app
