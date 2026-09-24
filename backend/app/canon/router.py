"""`GET /novelas/{novel_id}/versiones/{version}/hechos` (RF-CANON-03)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query

from app.canon import service
from app.canon.schemas import HechoVigente
from app.commons.errores import problemas
from app.commons.esquemas import sin_nulo
from app.commons.recursos import Recursos, recursos

router = APIRouter(tags=["canon"])


@router.get(
    "/novelas/{novel_id}/versiones/{version}/hechos",
    operation_id="listarHechos",
    response_model=list[HechoVigente],
    responses=problemas(404, 500),
)
async def listar_hechos(
    novel_id: UUID,
    version: Annotated[int, Path(ge=1)],
    r: Annotated[Recursos, Depends(recursos)],
    capitulo: Annotated[int | None, Query(ge=1, json_schema_extra=sin_nulo())] = None,
) -> list[HechoVigente]:
    return await service.listar_hechos(r.db, str(novel_id), version, capitulo=capitulo)
