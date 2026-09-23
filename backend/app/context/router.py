"""Endpoints de `context/`.

Las cuatro skills del sistema que este hito entrega, expuestas con contrato:
`ensamblar-contexto`, `recuperar-fragmentos`, `construir-anticontexto` y
`muestrear-voz` (esta ultima, dentro del ensamblado, como capa Estilo).

El ensamblado se consulta por API a proposito: el reparto resultante es lo que
permite ajustar el presupuesto con datos en vez de a ojo.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.commons.config import Umbrales
from app.commons.db.conexion import Conexion
from app.context import models, schemas, service


def conexion_de_la_instancia(peticion: Request) -> Conexion:
    conexion: Conexion = peticion.app.state.conexion
    return conexion


def umbrales_de_la_instancia(peticion: Request) -> Umbrales:
    umbrales: Umbrales = peticion.app.state.umbrales
    return umbrales


Base = Annotated[Conexion, Depends(conexion_de_la_instancia)]
Config = Annotated[Umbrales, Depends(umbrales_de_la_instancia)]

router = APIRouter(prefix="/context", tags=["context"])


@router.post("/ensamblados")
async def ensamblar(
    datos: schemas.PeticionDeEnsamblado, base: Base, umbrales: Config
) -> schemas.ContextoEnsamblado:
    """RF-CTX-01 a RF-CTX-06. Falla con 422 si no cabe: nunca trunca."""
    return service.ensamblar(base, umbrales, datos)


@router.post("/fragmentos", status_code=status.HTTP_201_CREATED)
async def indexar(datos: schemas.NuevoFragmento, base: Base, umbrales: Config) -> models.Fragmento:
    return service.indexar_fragmento(base, umbrales, datos)


@router.post("/recuperaciones")
async def recuperar(
    datos: schemas.PeticionDeRecuperacion, base: Base
) -> list[schemas.FragmentoRecuperado]:
    """RF-CTX-07. Filtro relacional por entidades y despues similitud."""
    return service.recuperar_fragmentos(base, datos.entidades, datos.consulta, datos.maximo)


@router.post("/usos", status_code=status.HTTP_201_CREATED)
async def registrar_uso(datos: schemas.NuevoUso, base: Base) -> models.UsoDeRecurso:
    return service.registrar_uso(base, datos)


@router.get("/escenas/{escena_id}/anticontexto")
async def anticontexto(
    escena_id: int, base: Base, umbrales: Config, personajes: str = ""
) -> schemas.Anticontexto:
    """RF-CTX-08, RF-CTX-12. La ventana sale de `config/thresholds.yaml`."""
    presentes = [int(pieza) for pieza in personajes.split(",") if pieza.strip()]
    return service.construir_anticontexto(
        base, escena_id, presentes, umbrales.contexto.anticontexto_ventana_escenas
    )


@router.get("/escenas/{escena_id}/niveles")
async def niveles(escena_id: int, base: Base) -> list[models.NivelDeCompresion]:
    """RF-CTX-09. Que resoluciones hay disponibles para esta escena."""
    return service.niveles_disponibles(base, escena_id)
