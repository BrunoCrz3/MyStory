"""Rutas `/novelas`: traducen HTTP a llamadas del servicio y nada más."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.commons.errores import problemas
from app.commons.recursos import Recursos, recursos
from app.intake.service import BriefNovela
from app.novel import service
from app.novel.schemas import ListaNovelas, Novela

router = APIRouter(tags=["novelas"])

_LOCATION = {
    "Location": {
        "description": "URI de la novela creada.",
        "schema": {"type": "string", "format": "uri-reference"},
    }
}


@router.get(
    "/novelas",
    operation_id="listarNovelas",
    response_model=ListaNovelas,
    responses=problemas(500),
)
async def listar_novelas(
    r: Annotated[Recursos, Depends(recursos)],
    limite: Annotated[int, Query(ge=1, le=100)] = 20,
    desplazamiento: Annotated[int, Query(ge=0)] = 0,
) -> ListaNovelas:
    return await service.listar_novelas(r.db, limite=limite, desplazamiento=desplazamiento)


@router.post(
    "/novelas",
    operation_id="crearNovela",
    status_code=201,
    response_model=Novela,
    response_model_exclude_none=False,
    responses={201: {"headers": _LOCATION}, **problemas(400, 422, 500)},
)
async def crear_novela(
    brief: BriefNovela, response: Response, r: Annotated[Recursos, Depends(recursos)]
) -> Novela:
    novela = await service.crear_novela(r.db, r.config, brief)
    response.headers["Location"] = f"/novelas/{novela.novel_id}"
    return novela


@router.get(
    "/novelas/{novel_id}",
    operation_id="obtenerNovela",
    response_model=Novela,
    responses=problemas(404, 500),
)
async def obtener_novela(novel_id: UUID, r: Annotated[Recursos, Depends(recursos)]) -> Novela:
    return await service.obtener_novela(r.db, str(novel_id))
