"""Endpoints de `novel/`. Traduce HTTP a llamadas del servicio y nada mas.

Si algo de aqui tuviera un `if` sobre una regla del mundo, la regla estaria en
el sitio equivocado. Los errores de dominio suben tal cual: los traduce el
handler central de `commons/http.py`.

Todos son `async` a proposito. La conexion se abre en el hilo del bucle de
eventos y SQLite solo la deja usar ahi; un endpoint sincrono correria en el pool
de hilos y fallaria en voz alta.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.commons.db.conexion import Conexion
from app.novel import models, schemas, service


def conexion_de_la_instancia(peticion: Request) -> Conexion:
    conexion: Conexion = peticion.app.state.conexion
    return conexion


Base = Annotated[Conexion, Depends(conexion_de_la_instancia)]

router = APIRouter(prefix="/novel", tags=["novel"])
CREADO = status.HTTP_201_CREATED


# --- Arbol estructural ----------------------------------------------------


@router.post("/obra", status_code=CREADO)
async def crear_obra(datos: schemas.NuevaObra, base: Base) -> models.Obra:
    return service.crear_obra(base, datos)


@router.get("/obra")
async def leer_obra(base: Base) -> models.Obra:
    return service.obtener_obra(base)


@router.post("/partes", status_code=CREADO)
async def crear_parte(datos: schemas.NuevaParte, base: Base) -> models.Parte:
    return service.crear_parte(base, datos)


@router.get("/partes")
async def listar_partes(base: Base) -> list[models.Parte]:
    return service.listar(base, models.Parte)


@router.post("/capitulos", status_code=CREADO)
async def crear_capitulo(datos: schemas.NuevoCapitulo, base: Base) -> models.Capitulo:
    return service.crear_capitulo(base, datos)


@router.get("/capitulos")
async def listar_capitulos(base: Base) -> list[models.Capitulo]:
    return service.listar(base, models.Capitulo)


@router.post("/escenas", status_code=CREADO)
async def crear_escena(datos: schemas.NuevaEscena, base: Base) -> models.Escena:
    return service.crear_escena(base, datos)


@router.get("/escenas")
async def listar_escenas(base: Base) -> list[models.Escena]:
    return service.listar(base, models.Escena)


@router.get("/escenas/{escena_id}")
async def leer_escena(escena_id: int, base: Base) -> models.Escena:
    return service.obtener_escena(base, escena_id)


@router.post("/escenas/{escena_id}/transicion")
async def transicionar_escena(
    escena_id: int, datos: schemas.NuevaTransicion, base: Base
) -> models.Escena:
    """Toda transicion del diagrama menos una.

    `aceptada` no sale por aqui: tiene su propia puerta en `process/`, que es
    donde el autor firma la aceptacion y donde se recoge lo que la acompana
    --si edito el texto, que version acepta--. Pedirla aqui responde 403.
    """
    return service.transicionar_escena(base, escena_id, datos.destino)


@router.post("/hilos/{hilo_id}/estado")
async def transicionar_hilo(
    hilo_id: int, datos: schemas.NuevoEstadoDeHilo, base: Base
) -> models.HiloDeTrama:
    return service.transicionar_hilo(base, hilo_id, datos.destino)


@router.get("/hilos/abiertos")
async def hilos_abiertos(base: Base) -> list[models.HiloDeTrama]:
    return service.hilos_abiertos(base)


@router.post("/beats", status_code=CREADO)
async def crear_beat(datos: schemas.NuevoBeat, base: Base) -> models.Beat:
    return service.crear_beat(base, datos)


@router.get("/beats")
async def listar_beats(base: Base) -> list[models.Beat]:
    return service.listar(base, models.Beat)


# --- Entidades narrativas -------------------------------------------------


@router.post("/personajes", status_code=CREADO)
async def crear_personaje(datos: schemas.NuevoPersonaje, base: Base) -> models.Personaje:
    return service.crear_personaje(base, datos)


@router.get("/personajes")
async def listar_personajes(base: Base) -> list[models.Personaje]:
    return service.listar(base, models.Personaje)


@router.post("/voces", status_code=CREADO)
async def crear_voz(datos: schemas.NuevaVoz, base: Base) -> models.Voz:
    return service.crear_voz(base, datos)


@router.get("/voces")
async def listar_voces(base: Base) -> list[models.Voz]:
    return service.listar(base, models.Voz)


@router.post("/arcos", status_code=CREADO)
async def crear_arco(datos: schemas.NuevoArco, base: Base) -> models.Arco:
    return service.crear_arco(base, datos)


@router.get("/arcos")
async def listar_arcos(base: Base) -> list[models.Arco]:
    return service.listar(base, models.Arco)


@router.post("/hilos-de-trama", status_code=CREADO)
async def crear_hilo(datos: schemas.NuevoHiloDeTrama, base: Base) -> models.HiloDeTrama:
    return service.crear_hilo_de_trama(base, datos)


@router.get("/hilos-de-trama")
async def listar_hilos(base: Base) -> list[models.HiloDeTrama]:
    return service.listar(base, models.HiloDeTrama)


@router.post("/lugares", status_code=CREADO)
async def crear_lugar(datos: schemas.NuevoLugar, base: Base) -> models.Lugar:
    return service.crear_lugar(base, datos)


@router.get("/lugares")
async def listar_lugares(base: Base) -> list[models.Lugar]:
    return service.listar(base, models.Lugar)


@router.post("/facciones", status_code=CREADO)
async def crear_faccion(datos: schemas.NuevaFaccion, base: Base) -> models.Faccion:
    return service.crear_faccion(base, datos)


@router.get("/facciones")
async def listar_facciones(base: Base) -> list[models.Faccion]:
    return service.listar(base, models.Faccion)


@router.post("/artefactos", status_code=CREADO)
async def crear_artefacto(datos: schemas.NuevoArtefacto, base: Base) -> models.Artefacto:
    return service.crear_artefacto(base, datos)


@router.get("/artefactos")
async def listar_artefactos(base: Base) -> list[models.Artefacto]:
    return service.listar(base, models.Artefacto)


@router.post("/novums", status_code=CREADO)
async def crear_novum(datos: schemas.NuevoNovum, base: Base) -> models.Novum:
    return service.crear_novum(base, datos)


@router.get("/novums")
async def listar_novums(base: Base) -> list[models.Novum]:
    return service.listar(base, models.Novum)


@router.get("/novums/{novum_id}/verificacion")
async def verificar_novum(novum_id: int, base: Base) -> models.Novum:
    """A-51: responde 422 si el novum no impone ninguna regla del mundo."""
    return service.verificar_novum(base, novum_id)


@router.post("/reglas-del-mundo", status_code=CREADO)
async def crear_regla(datos: schemas.NuevaReglaDelMundo, base: Base) -> models.ReglaDelMundo:
    return service.crear_regla_del_mundo(base, datos)


@router.get("/reglas-del-mundo")
async def listar_reglas(base: Base) -> list[models.ReglaDelMundo]:
    return service.listar(base, models.ReglaDelMundo)


@router.post("/terminos-canonicos", status_code=CREADO)
async def crear_termino(datos: schemas.NuevoTerminoCanonico, base: Base) -> models.TerminoCanonico:
    return service.crear_termino_canonico(base, datos)


@router.get("/terminos-canonicos")
async def listar_terminos(base: Base) -> list[models.TerminoCanonico]:
    return service.listar(base, models.TerminoCanonico)


@router.post("/temas", status_code=CREADO)
async def crear_tema(datos: schemas.NuevoTema, base: Base) -> models.Tema:
    return service.crear_tema(base, datos)


@router.get("/temas")
async def listar_temas(base: Base) -> list[models.Tema]:
    return service.listar(base, models.Tema)


@router.post("/motivos", status_code=CREADO)
async def crear_motivo(datos: schemas.NuevoMotivo, base: Base) -> models.Motivo:
    return service.crear_motivo(base, datos)


@router.get("/motivos")
async def listar_motivos(base: Base) -> list[models.Motivo]:
    return service.listar(base, models.Motivo)


@router.post("/voces-narrativas", status_code=CREADO)
async def crear_voz_narrativa(datos: schemas.NuevaVozNarrativa, base: Base) -> models.VozNarrativa:
    return service.crear_voz_narrativa(base, datos)


@router.get("/voces-narrativas")
async def listar_voces_narrativas(base: Base) -> list[models.VozNarrativa]:
    return service.listar(base, models.VozNarrativa)


# --- Fabula ---------------------------------------------------------------


@router.post("/eventos", status_code=CREADO)
async def crear_evento(datos: schemas.NuevoEvento, base: Base) -> models.Evento:
    return service.crear_evento(base, datos)


@router.get("/eventos")
async def listar_eventos(base: Base) -> list[models.Evento]:
    return service.listar(base, models.Evento)


@router.post("/eventos/{evento_id}/escenas/{escena_id}", status_code=CREADO)
async def narrar_evento_en_escena(evento_id: int, escena_id: int, base: Base) -> None:
    service.narrar_evento_en_escena(base, evento_id, escena_id)


@router.get("/eventos/{evento_id}/escenas")
async def escenas_del_evento(evento_id: int, base: Base) -> list[models.Escena]:
    return service.escenas_donde_se_narra(base, evento_id)


@router.post("/objetivos", status_code=CREADO)
async def crear_objetivo(datos: schemas.NuevoObjetivo, base: Base) -> models.Objetivo:
    return service.crear_objetivo(base, datos)


@router.get("/objetivos")
async def listar_objetivos(base: Base) -> list[models.Objetivo]:
    return service.listar(base, models.Objetivo)
