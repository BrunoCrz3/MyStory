"""Rutas de generación: lanzar, listar y consultar el progreso."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.commons.errores import problemas
from app.commons.recursos import Recursos, recursos
from app.process import cola
from app.process.schemas import Generacion

router = APIRouter(tags=["generacion"])

_LOCATION = {
    "Location": {
        "description": "URI del recurso de progreso.",
        "schema": {"type": "string", "format": "uri-reference"},
    }
}


@router.get(
    "/novelas/{novel_id}/generaciones",
    operation_id="listarGeneraciones",
    response_model=list[Generacion],
    response_model_exclude_none=False,
    responses=problemas(404, 500),
)
async def listar_generaciones(
    novel_id: UUID, r: Annotated[Recursos, Depends(recursos)]
) -> list[Generacion]:
    return await cola.listar_generaciones(r, str(novel_id))


@router.post(
    "/novelas/{novel_id}/generaciones",
    operation_id="lanzarGeneracion",
    status_code=202,
    response_model=Generacion,
    responses={202: {"headers": _LOCATION}, **problemas(404, 409, 422, 500)},
)
async def lanzar_generacion(
    novel_id: UUID, response: Response, r: Annotated[Recursos, Depends(recursos)]
) -> Generacion:
    g = await cola.lanzar_generacion(r, str(novel_id))
    response.headers["Location"] = f"/novelas/{novel_id}/generaciones/{g.generacion_id}"
    return g


@router.get(
    "/novelas/{novel_id}/generaciones/{generacion_id}",
    operation_id="obtenerGeneracion",
    response_model=Generacion,
    responses=problemas(404, 500),
)
async def obtener_generacion(
    novel_id: UUID, generacion_id: UUID, r: Annotated[Recursos, Depends(recursos)]
) -> Generacion:
    return await cola.obtener_generacion(r, str(novel_id), str(generacion_id))
