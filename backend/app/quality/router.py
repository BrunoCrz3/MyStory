"""Endpoints de `quality/`.

Dos skills del sistema con contrato: `medir-calidad`, que usa el `critico`, y
`verificar-continuidad`, que usa el `verificador`. Los dos corren en paralelo
sobre la misma escena porque solo leen.

La puerta de higiene se expone aparte a proposito. Corre dentro de `criticar`,
pero tambien tiene que poder correr sola y antes: es determinista, vale
milisegundos y lo que protege es el punto unico de promocion.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.commons.config import Umbrales
from app.commons.db.conexion import Conexion
from app.quality import models, schemas, service


def conexion_de_la_instancia(peticion: Request) -> Conexion:
    conexion: Conexion = peticion.app.state.conexion
    return conexion


def umbrales_de_la_instancia(peticion: Request) -> Umbrales:
    umbrales: Umbrales = peticion.app.state.umbrales
    return umbrales


Base = Annotated[Conexion, Depends(conexion_de_la_instancia)]
Config = Annotated[Umbrales, Depends(umbrales_de_la_instancia)]

router = APIRouter(prefix="/quality", tags=["quality"])


@router.post("/higiene")
async def higiene(
    datos: schemas.PeticionDeCritica, base: Base, umbrales: Config
) -> schemas.ResultadoDeHigiene:
    """A-47, RF-QUA-06. Determinista y sin modelo."""
    return service.puerta_de_higiene(base, umbrales, datos.texto, datos.escena_id)


@router.post("/criticas")
async def criticar(
    datos: schemas.PeticionDeCritica, base: Base, umbrales: Config
) -> schemas.Critica:
    """`medir-calidad`. Responde 422 si el borrador no pasa la puerta."""
    return service.criticar(base, umbrales, datos)


@router.post("/continuidad")
async def continuidad(
    datos: schemas.PeticionDeCritica, base: Base
) -> list[schemas.DefectoDetectado]:
    """`verificar-continuidad`, los cuatro ejes contra el canon en `t`."""
    return service.verificar_continuidad(base, datos)


@router.get("/escenas/{escena_id}/criticas")
async def criticas_de_la_escena(escena_id: int, base: Base) -> list[models.InformeDeCritica]:
    return service.informes_de(base, escena_id)


@router.get("/escenas/{escena_id}/regresiones")
async def regresiones(escena_id: int, version: int, base: Base) -> list[schemas.Regresion]:
    """A-50, RF-QUA-08: que ha empeorado esta version respecto de la anterior."""
    return service.comparar_con_anterior(base, escena_id, version)


@router.get("/dimensiones")
async def dimensiones(base: Base) -> list[models.DimensionDeCalidad]:
    """Las catorce `T`, con su nivel de aplicacion y su metodo de medicion."""
    return service.catalogo_de_dimensiones(base)
