"""Endpoints de `process/`. Traduce HTTP a llamadas del servicio y nada mas.

Dos puertas de aqui no son endpoints cualesquiera:

- **`POST /process/escenas/{id}/aceptacion`** es la unica del sistema por la que
  una escena llega a `aceptada`. La transicion generica de `novel/` la rechaza
  (RF-PROC-07, P-19).
- **`POST /process/esquema`** es, en v1, la unica forma de replanificar, y por
  eso pide un motivo: esas decisiones son las etiquetas con las que se calibran
  los umbrales de deriva (RF-PROC-13).

El cliente del modelo se construye **tarde**, en la primera generacion. Si se
construyera al arrancar, una instancia sin credencial no podria ni servir
`/salud` ni aplicar migraciones, y las dos cosas son anteriores a escribir una
linea de prosa.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.commons.config import Umbrales
from app.commons.db.conexion import Conexion
from app.commons.llm.cliente import ClienteDelModelo, Generador
from app.commons.tokens.en_vuelo import PoolEnVuelo
from app.process import models, schemas, service
from app.process.models import ComponenteDeDeriva
from app.process.orquestador import CerrojoDeGeneracion

CREADO = status.HTTP_201_CREATED


def conexion_de_la_instancia(peticion: Request) -> Conexion:
    conexion: Conexion = peticion.app.state.conexion
    return conexion


def umbrales_de_la_instancia(peticion: Request) -> Umbrales:
    umbrales: Umbrales = peticion.app.state.umbrales
    return umbrales


def pool_de_la_instancia(peticion: Request) -> PoolEnVuelo:
    pool: PoolEnVuelo = peticion.app.state.pool_en_vuelo
    return pool


def cerrojo_de_la_instancia(peticion: Request) -> CerrojoDeGeneracion:
    cerrojo: CerrojoDeGeneracion = peticion.app.state.cerrojo_de_generacion
    return cerrojo


def modelo_de_la_instancia(peticion: Request) -> Generador:
    modelo: Generador | None = getattr(peticion.app.state, "modelo", None)
    if modelo is None:
        modelo = ClienteDelModelo(peticion.app.state.umbrales)
        peticion.app.state.modelo = modelo
    return modelo


Base = Annotated[Conexion, Depends(conexion_de_la_instancia)]
Config = Annotated[Umbrales, Depends(umbrales_de_la_instancia)]
Pool = Annotated[PoolEnVuelo, Depends(pool_de_la_instancia)]
Cerrojo = Annotated[CerrojoDeGeneracion, Depends(cerrojo_de_la_instancia)]
Modelo = Annotated[Generador, Depends(modelo_de_la_instancia)]

router = APIRouter(prefix="/process", tags=["process"])


# --- Esquema y brief ------------------------------------------------------


@router.post("/esquema", status_code=CREADO)
async def fijar_hito(datos: schemas.NuevoHito, base: Base) -> models.Esquema:
    """RF-PROC-13. Registra el plan vigente y por que se movio."""
    return service.fijar_hito(base, datos)


@router.get("/esquema")
async def esquema(base: Base) -> schemas.EsquemaDeclarado:
    return service.esquema_declarado(base)


@router.get("/esquema/hitos")
async def hitos(base: Base) -> list[models.Esquema]:
    return service.hitos(base)


@router.post("/briefs", status_code=CREADO)
async def crear_brief(datos: schemas.NuevoBrief, base: Base) -> schemas.BriefCompleto:
    return service.crear_brief(base, datos)


@router.get("/escenas/{escena_id}/brief")
async def brief_de_la_escena(escena_id: int, base: Base) -> schemas.BriefCompleto:
    return service.brief_de(base, escena_id)


# --- Generacion y versiones -----------------------------------------------


@router.post("/escenas/{escena_id}/borradores", status_code=CREADO)
async def generar_borrador(
    escena_id: int,
    datos: schemas.PeticionDeBorrador,
    base: Base,
    umbrales: Config,
    modelo: Modelo,
    pool: Pool,
    cerrojo: Cerrojo,
) -> models.Version:
    """El `redactor`. Una sola escena en generacion a la vez (RNF-09)."""
    return await service.generar_borrador(base, umbrales, modelo, pool, cerrojo, escena_id, datos)


@router.post("/escenas/{escena_id}/versiones", status_code=CREADO)
async def anotar_version_del_autor(
    escena_id: int, datos: schemas.NuevaVersionDelAutor, base: Base
) -> models.Version:
    return service.anotar_version_del_autor(base, escena_id, datos.texto)


@router.get("/escenas/{escena_id}/versiones")
async def versiones(escena_id: int, base: Base) -> list[models.Version]:
    return service.versiones_de(base, escena_id)


@router.get("/escenas/{escena_id}/traza")
async def traza(escena_id: int, base: Base) -> list[schemas.VersionConTraza]:
    """RNF-06, P-28: la trayectoria de cada agente, consultable a posteriori."""
    return service.traza_de(base, escena_id)


@router.get("/escenas/{escena_id}/registros")
async def registros(escena_id: int, base: Base) -> list[models.RegistroDeGeneracion]:
    return service.registros_de(base, escena_id)


# --- Orquestacion y aceptacion --------------------------------------------


@router.get("/escenas/{escena_id}/paso")
async def paso(escena_id: int, base: Base, umbrales: Config) -> schemas.PasoSugerido:
    """RF-PROC-05. Lo decide la maquina de estados leyendo la base."""
    return service.siguiente_paso_de(base, umbrales, escena_id)


@router.post("/escenas/{escena_id}/aceptacion")
async def aceptar(
    escena_id: int, datos: schemas.PeticionDeAceptacion, base: Base
) -> schemas.Aceptacion:
    """La firma del autor. Ningun agente pasa por aqui (RF-PROC-07)."""
    return service.aceptar_escena(base, escena_id, datos)


@router.get("/escenas/{escena_id}/adelantos")
async def adelantos(escena_id: int, base: Base) -> list[models.RestriccionDeDestino]:
    """RF-PROC-11, P-41: destinos de briefs posteriores que esta escena ya cumple."""
    return service.adelantos(base, escena_id)


# --- Deriva ---------------------------------------------------------------


@router.post("/escenas/{escena_id}/deriva", status_code=CREADO)
async def medir_deriva(escena_id: int, base: Base, umbrales: Config) -> schemas.VectorDeDeriva:
    """RF-PROC-08. Se mide una vez por escena aceptada, contra el canon en t."""
    return service.medir_deriva(base, umbrales, escena_id)


@router.get("/escenas/{escena_id}/deriva")
async def deriva_de_la_escena(
    escena_id: int, base: Base, umbrales: Config
) -> schemas.VectorDeDeriva:
    return service.deriva_de(base, umbrales, escena_id)


@router.get("/escenas/{escena_id}/deriva/recalculada")
async def deriva_recalculada(
    escena_id: int, base: Base
) -> dict[ComponenteDeDeriva, schemas.Componente]:
    """RF-PROC-12: el mismo vector, reconstruido solo desde los ingredientes."""
    return service.recalcular_deriva(base, escena_id)


@router.get("/deriva")
async def historico(base: Base, umbrales: Config) -> list[schemas.VectorDeDeriva]:
    """La serie por escena aceptada. Es lo que v1 acumula para poder calibrar."""
    return service.historico(base, umbrales)
