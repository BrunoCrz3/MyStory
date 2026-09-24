"""La app de verdad con los dos dobles, como proceso aparte (plan P27).

`python -m tests.e2e.app_con_dobles --port N` levanta `crear_app` con `ModeloGuionizado` y
`RegistroTrazas` detrás de `uvicorn`, igual que el lanzador: interfaz local y un worker. Así
una prueba puede matar el proceso de verdad a mitad de novela y rearrancarlo sobre la misma
base. `STORYMAKER_E2E_RETARDO_S` hace que cada llamada al doble tarde lo que diga, para que
haya tiempo de matarlo en el capítulo que se quiere. Con `STORYMAKER_E2E_RENDER=real`,
`render_visual` es el de producción (servidor MCP y página de lectura del entorno) y no el doble.
"""

from __future__ import annotations

import argparse
import os

import anyio
import uvicorn
from fastapi import FastAPI

from app.commons.config import Config, cargar_config
from app.commons.llm import Peticion, Recuento, Respuesta
from app.main import crear_app
from tests.dobles.guiones import guion_completo
from tests.dobles.modelo import ModeloGuionizado
from tests.dobles.render import RenderGuionizado
from tests.dobles.trazador import RegistroTrazas


class ModeloConRetardo(ModeloGuionizado):
    def __init__(self, config: Config, retardo_s: float) -> None:
        super().__init__(config)
        self.retardo_s = retardo_s

    async def generar(self, peticion: Peticion, recuento: Recuento) -> Respuesta:
        await anyio.sleep(self.retardo_s)
        return await super().generar(peticion, recuento)


def crear() -> FastAPI:
    cfg = cargar_config()
    modelo = ModeloConRetardo(cfg, float(os.environ.get("STORYMAKER_E2E_RETARDO_S", "0")))
    guion_completo(modelo)
    real = os.environ.get("STORYMAKER_E2E_RENDER") == "real"
    return crear_app(
        cfg,
        cliente_modelo=modelo,
        trazador=RegistroTrazas(),
        render_visual=None if real else RenderGuionizado(),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    uvicorn.run(crear(), host="127.0.0.1", port=args.port, workers=1)
