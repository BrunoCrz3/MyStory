"""Endpoints de `canon/`.

Los cuatro primeros son `consultar-canon`, la skill del sistema que usan el
planificador, el redactor y el verificador: snapshot en `t`, estado epistemico y
promesas abiertas (`architecture.md` § Skills del sistema). No es una
instruccion suelta en un prompt: es una operacion del backend con contrato.

`POST /canon/consolidaciones` es el unico punto que modifica el canon.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.canon import models, schemas, service
from app.commons.config import Umbrales
from app.commons.db.conexion import Conexion


def conexion_de_la_instancia(peticion: Request) -> Conexion:
    conexion: Conexion = peticion.app.state.conexion
    return conexion


def umbrales_de_la_instancia(peticion: Request) -> Umbrales:
    umbrales: Umbrales = peticion.app.state.umbrales
    return umbrales


Base = Annotated[Conexion, Depends(conexion_de_la_instancia)]
Config = Annotated[Umbrales, Depends(umbrales_de_la_instancia)]

router = APIRouter(prefix="/canon", tags=["canon"])


# --- consultar-canon ------------------------------------------------------


@router.get("/escenas/{escena_id}/snapshot")
async def snapshot(escena_id: int, base: Base) -> schemas.SnapshotDerivado:
    return service.snapshot_en(base, escena_id)


@router.get("/escenas/{escena_id}/hechos-vigentes")
async def hechos_vigentes(escena_id: int, base: Base) -> list[models.HechoCanonico]:
    return service.hechos_vigentes_en(base, escena_id)


@router.get("/personajes/{personaje_id}/conocimiento")
async def conocimiento(
    personaje_id: int, hasta_escena_id: int, base: Base
) -> list[models.EstadoEpistemico]:
    """Pregunta de competencia 1: que sabe este personaje, y desde que escena."""
    return service.que_sabe(base, personaje_id, hasta_escena_id)


@router.get("/escenas/{escena_id}/promesas-abiertas")
async def promesas_abiertas(escena_id: int, base: Base) -> list[models.PromesaNarrativa]:
    return service.promesas_abiertas_en(base, escena_id)


@router.get("/escenas/{escena_id}/revelaciones-pendientes")
async def revelaciones_pendientes(escena_id: int, base: Base) -> list[schemas.RevelacionPendiente]:
    """Pregunta de competencia 9 y P-40: que no se puede contar todavia en `t`."""
    return service.revelaciones_pendientes(base, escena_id)


# --- Consolidacion --------------------------------------------------------


@router.post("/consolidaciones", status_code=status.HTTP_201_CREATED)
async def consolidar(datos: schemas.Consolidacion, base: Base) -> schemas.ResultadoDeConsolidacion:
    """Idempotente por `escena_id` + `version` (RI-05, RF-CANON-08)."""
    return service.consolidar_escena(base, datos)


@router.get("/escenas/{escena_id}/hechos")
async def hechos_de_la_escena(escena_id: int, base: Base) -> list[models.HechoCanonico]:
    return service.hechos_establecidos_en(base, escena_id)


# --- Ciclos de vida -------------------------------------------------------


@router.post("/hechos/{hecho_id}/transicion")
async def transicionar_hecho(
    hecho_id: int, datos: schemas.TransicionDeHecho, base: Base
) -> models.HechoCanonico:
    return service.transicionar_hecho(base, hecho_id, datos.destino)


@router.post("/promesas/{promesa_id}/transicion")
async def transicionar_promesa(
    promesa_id: int, datos: schemas.TransicionDePromesa, base: Base
) -> models.PromesaNarrativa:
    return service.transicionar_promesa(base, promesa_id, datos.destino, datos.escena_de_pago_id)


# --- Contradicciones, estancamiento y retcon ------------------------------


@router.post("/contradicciones/deteccion")
async def detectar(base: Base) -> list[models.Contradiccion]:
    return service.detectar_contradicciones(base)


@router.get("/estancamiento")
async def estancamiento(base: Base, umbrales: Config) -> schemas.InformeDeEstancamiento:
    """RF-CANON-14. Los tres umbrales salen de `config/thresholds.yaml`.

    Siguen en `null` y son `[historico]`: la consulta informa de que no hay
    umbral declarado en vez de fallar. Medir no es cerrar el paso.
    """
    return service.estancados(
        base,
        umbral_arco=umbrales.continuidad.escenas_sin_avanzar_arco,
        umbral_hilo=umbrales.continuidad.escenas_sin_avanzar_hilo,
        umbral_promesa=umbrales.continuidad.promesas_pendientes_max,
    )


@router.get("/hechos/{hecho_id}/retcon-simulado")
async def retcon_simulado(hecho_id: int, base: Base) -> schemas.SimulacionDeRetcon:
    """RF-CANON-09: responde que escenas quedarian invalidadas. No las marca."""
    return service.simular_retcon(base, hecho_id)
