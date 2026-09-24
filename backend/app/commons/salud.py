"""`GET /salud` (RF-META-01): lo que el frontend necesita saber sin adivinar."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.commons.errores import problemas
from app.commons.esquemas import opcional
from app.commons.recursos import Recursos, recursos

VERSION_API = "1.1.0"

router = APIRouter()


class Salud(BaseModel):
    estado: Literal["ok", "degradado"]
    version_api: str
    gate_lean_activo: bool
    cerrar_el_paso: bool
    tokens_en_vuelo: Annotated[int, Field(ge=0)] | None = opcional()
    tokens_en_vuelo_total: Annotated[int, Field(ge=0)] | None = opcional()
    trabajos_en_cola: Annotated[int, Field(ge=0)] | None = opcional()


@router.get(
    "/salud",
    operation_id="obtenerSalud",
    tags=["meta"],
    response_model=Salud,
    response_model_exclude_none=True,
    responses=problemas(500),
)
async def obtener_salud(r: Annotated[Recursos, Depends(recursos)]) -> Salud:
    u = r.config.umbrales
    return Salud(
        estado="degradado" if r.trazador.degradado else "ok",
        version_api=VERSION_API,
        gate_lean_activo=u.formal.gate_activo,
        cerrar_el_paso=u.medicion.cerrar_el_paso,
        tokens_en_vuelo=r.pool.ocupado,
        tokens_en_vuelo_total=r.pool.total,
        trabajos_en_cola=await r.contar_cola() if r.contar_cola is not None else None,
    )
