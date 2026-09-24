"""Rutas de lectura por versión: traducen HTTP a llamadas del servicio y nada más."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path

from app.commons.errores import problemas
from app.commons.recursos import Recursos, recursos
from app.versioning import service, solicitud
from app.versioning.schemas import (
    Capitulo,
    NuevaSolicitudCambio,
    SolicitudCambio,
    Version,
    VersionResumen,
)

router = APIRouter(tags=["lectura"])
# Las solicitudes de cambio y su confirmación son de la regeneración, no de la lectura.
regeneracion = APIRouter(tags=["regeneracion"])

NumeroVersion = Annotated[int, Path(ge=1)]
NumeroCapitulo = Annotated[int, Path(ge=1)]


@router.get(
    "/novelas/{novel_id}/versiones",
    operation_id="listarVersiones",
    response_model=list[VersionResumen],
    response_model_exclude_none=False,
    responses=problemas(404, 500),
)
async def listar_versiones(
    novel_id: UUID, r: Annotated[Recursos, Depends(recursos)]
) -> list[VersionResumen]:
    return await service.listar_versiones(r.db, str(novel_id))


@router.get(
    "/novelas/{novel_id}/versiones/{version}",
    operation_id="obtenerVersion",
    response_model=Version,
    response_model_exclude_none=False,
    responses=problemas(404, 500),
)
async def obtener_version(
    novel_id: UUID, version: NumeroVersion, r: Annotated[Recursos, Depends(recursos)]
) -> Version:
    return await service.obtener_version(r.db, str(novel_id), version)


@router.get(
    "/novelas/{novel_id}/versiones/{version}/capitulos",
    operation_id="listarCapitulos",
    response_model=list[Capitulo],
    response_model_exclude_none=False,
    responses=problemas(404, 500),
)
async def listar_capitulos(
    novel_id: UUID, version: NumeroVersion, r: Annotated[Recursos, Depends(recursos)]
) -> list[Capitulo]:
    return await service.listar_capitulos(r.db, str(novel_id), version)


@router.get(
    "/novelas/{novel_id}/versiones/{version}/capitulos/{numero}",
    operation_id="obtenerCapitulo",
    response_model=Capitulo,
    response_model_exclude_none=False,
    responses=problemas(404, 500),
)
async def obtener_capitulo(
    novel_id: UUID,
    version: NumeroVersion,
    numero: NumeroCapitulo,
    r: Annotated[Recursos, Depends(recursos)],
) -> Capitulo:
    return await service.obtener_capitulo(r.db, str(novel_id), version, numero)


@regeneracion.post(
    "/novelas/{novel_id}/solicitudes-cambio",
    operation_id="crearSolicitudCambio",
    status_code=201,
    response_model=SolicitudCambio,
    responses=problemas(404, 409, 422, 500),
)
async def crear_solicitud_cambio(
    novel_id: UUID, nueva: NuevaSolicitudCambio, r: Annotated[Recursos, Depends(recursos)]
) -> SolicitudCambio:
    return await solicitud.crear_solicitud(r.db, str(novel_id), nueva)


@regeneracion.get(
    "/novelas/{novel_id}/solicitudes-cambio/{solicitud_id}",
    operation_id="obtenerSolicitudCambio",
    response_model=SolicitudCambio,
    responses=problemas(404, 500),
)
async def obtener_solicitud_cambio(
    novel_id: UUID, solicitud_id: UUID, r: Annotated[Recursos, Depends(recursos)]
) -> SolicitudCambio:
    return await solicitud.obtener_solicitud(r.db, str(novel_id), str(solicitud_id))
