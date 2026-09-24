"""Rutas de lectura por versión: traducen HTTP a llamadas del servicio y nada más."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Response

from app.commons.errores import problemas
from app.commons.recursos import Recursos, recursos
from app.process.service import Generacion
from app.versioning import confirmar, service, solicitud
from app.versioning.schemas import (
    Capitulo,
    Ficha,
    NuevaSolicitudCambio,
    Portada,
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
    return await solicitud.crear_solicitud(r.db, r.config, str(novel_id), nueva)


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


@router.get(
    "/novelas/{novel_id}/versiones/{version}/ficha",
    operation_id="obtenerFicha",
    response_model=Ficha,
    responses=problemas(404, 500),
)
async def obtener_ficha(
    novel_id: UUID, version: NumeroVersion, r: Annotated[Recursos, Depends(recursos)]
) -> Ficha:
    return await service.obtener_ficha(r.db, str(novel_id), version)


@router.get(
    "/novelas/{novel_id}/versiones/{version}/portada",
    operation_id="obtenerPortada",
    response_model=Portada,
    responses=problemas(404, 500),
)
async def obtener_portada(
    novel_id: UUID, version: NumeroVersion, r: Annotated[Recursos, Depends(recursos)]
) -> Portada:
    return await service.obtener_portada(r.db, str(novel_id), version)


_LOCATION = {
    "Location": {
        "description": "URI del recurso de progreso.",
        "schema": {"type": "string", "format": "uri-reference"},
    }
}


@regeneracion.post(
    "/novelas/{novel_id}/solicitudes-cambio/{solicitud_id}/confirmacion",
    operation_id="confirmarSolicitudCambio",
    status_code=202,
    response_model=Generacion,
    responses={202: {"headers": _LOCATION}, **problemas(404, 409, 422, 500)},
)
async def confirmar_solicitud_cambio(
    novel_id: UUID,
    solicitud_id: UUID,
    response: Response,
    r: Annotated[Recursos, Depends(recursos)],
) -> Generacion:
    generacion = await confirmar.confirmar(r, str(novel_id), str(solicitud_id))
    response.headers["Location"] = f"/novelas/{novel_id}/generaciones/{generacion.generacion_id}"
    return generacion
