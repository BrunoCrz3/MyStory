"""Endpoints de `findings/`.

Dos puertas y una bandeja. `POST /findings/escenas/{id}/extraccion` es la skill
`extraer-hallazgos`, que corre despues de consolidar;
`POST /findings/hallazgos/{id}/decision` es la firma del autor, y es la unica
via por la que un hallazgo sale de `propuesto` (RF-FIND-02, RF-FIND-05).

No hay endpoint para crear un hallazgo suelto. Todo hallazgo viene de una
extraccion, y toda extraccion viene de una escena consolidada: es la forma de
que no exista un segundo camino a memoria larga.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.commons.db.conexion import Conexion
from app.findings import models, schemas, service
from app.findings.models import ModoDeAdopcion


def conexion_de_la_instancia(peticion: Request) -> Conexion:
    conexion: Conexion = peticion.app.state.conexion
    return conexion


Base = Annotated[Conexion, Depends(conexion_de_la_instancia)]

router = APIRouter(prefix="/findings", tags=["findings"])


@router.post("/escenas/{escena_id}/extraccion", status_code=status.HTTP_201_CREATED)
async def extraer(
    escena_id: int, datos: schemas.PeticionDeExtraccion, base: Base
) -> schemas.ResultadoDeExtraccion:
    """`extraer-hallazgos`. Responde 409 si la escena no esta consolidada."""
    return service.extraer(base, escena_id, datos)


@router.post("/hallazgos/{hallazgo_id}/decision")
async def decidir(hallazgo_id: int, datos: schemas.DecisionDelAutor, base: Base) -> models.Hallazgo:
    """La firma del autor.

    Este endpoint **es** el autor: es la unica llamada del sistema que pasa
    `ModoDeAdopcion.HUMANA`, y por eso adoptar un hallazgo no se puede hacer
    desde dentro del proceso.
    """
    return service.decidir(base, hallazgo_id, datos, modo=ModoDeAdopcion.HUMANA)


@router.get("/hallazgos")
async def bandeja(base: Base) -> list[models.Hallazgo]:
    """Lo que espera decision del autor, y lo unico que hay que revisar."""
    return service.propuestos(base)


@router.get("/hallazgos/adoptados")
async def adoptados(base: Base) -> list[models.Hallazgo]:
    return service.adoptados(base)


@router.get("/escenas/{escena_id}/hallazgos")
async def de_la_escena(escena_id: int, base: Base) -> list[models.Hallazgo]:
    return service.hallazgos_de(base, escena_id)
