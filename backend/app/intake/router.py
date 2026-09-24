"""`POST /briefs/validacion`: valida un brief parcial sin crear nada (RF-INTAKE-01)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.commons.errores import problemas
from app.commons.recursos import Recursos, recursos
from app.intake import service
from app.intake.schemas import BriefNovelaParcial, ResultadoValidacionBrief

router = APIRouter(tags=["intake"])


@router.post(
    "/briefs/validacion",
    operation_id="validarBrief",
    response_model=ResultadoValidacionBrief,
    responses=problemas(422, 500),
)
async def validar_brief(
    brief: BriefNovelaParcial, r: Annotated[Recursos, Depends(recursos)]
) -> ResultadoValidacionBrief:
    return await service.validar_brief(r, brief)
