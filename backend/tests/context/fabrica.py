"""Mundo indexado para las pruebas de contexto.

Los vectores se dan a mano. No es un atajo: el ensamblado y la recuperacion no
dependen de **quien** produce el vector, y atarlos al modelo local convertiria
cada prueba en una descarga de dos gigas. Que el modelo local produzca vectores
de la dimension declarada es otra afirmacion, y tiene su propia prueba.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.canon import schemas as canon_schemas
from app.canon import service as canon
from app.canon.models import TipoDeHecho
from app.commons.config import Umbrales, cargar_umbrales
from app.commons.db.conexion import Conexion, abrir_conexion
from app.commons.db.migraciones import aplicar_migraciones
from app.context import schemas
from app.context import service as contexto
from app.context.models import Capa, NivelDeCompresion
from tests.canon.fabrica import Mundo, mundo


@contextmanager
def base_nueva() -> Iterator[Conexion]:
    with (
        tempfile.TemporaryDirectory() as carpeta,
        abrir_conexion(Path(carpeta) / "novel.db") as conexion,
    ):
        aplicar_migraciones(conexion)
        yield conexion


def umbrales() -> Umbrales:
    return cargar_umbrales()


def vector(semilla: float, dimension: int) -> list[float]:
    """Vector determinista y distinguible, no aleatorio: una prueba de orden
    necesita saber cual esta mas cerca."""
    return [semilla] * dimension


def indexar(
    base: Conexion,
    escena_id: int,
    texto: str,
    entidades: list[schemas.Referencia],
    semilla: float,
    dimension: int,
    nivel: NivelDeCompresion = NivelDeCompresion.ESCENA_LITERAL,
) -> int:
    return contexto.indexar_fragmento(
        base,
        umbrales(),
        schemas.NuevoFragmento(
            escena_id=escena_id,
            texto=texto,
            nivel=nivel,
            entidades=entidades,
            embedding=vector(semilla, dimension),
        ),
    ).id


def obra_indexada(base: Conexion, dimension: int) -> tuple[Mundo, list[int]]:
    """Cuatro escenas consolidadas, cada una con su fragmento literal."""
    creado = mundo(base, escenas=5)
    escenas: list[int] = []
    for paso in range(4):
        escena_id = creado.escena_consolidada(
            hechos=[
                creado.hecho(
                    TipoDeHecho.UBICACION,
                    sujeto=creado.ilia if paso % 2 == 0 else creado.baro,
                    lugar=creado.vado if paso % 2 == 0 else creado.orilla,
                )
            ]
        )
        indexar(
            base,
            escena_id,
            f"Escena {paso}: el agua subia y nadie dijo nada. " * 20,
            [schemas.Referencia(tipo="personaje", id=creado.ilia)],
            semilla=0.1 * (paso + 1),
            dimension=dimension,
        )
        escenas.append(escena_id)
    return creado, escenas


def peticion(
    creado: Mundo, escena_id: int, dimension: int, **extra: object
) -> schemas.PeticionDeEnsamblado:
    campos: dict[str, object] = {
        "escena_id": escena_id,
        "brief": "Ilia vuelve al vado y encuentra la puerta abierta.",
        "restriccion_de_destino": "La escena termina con Ilia dentro y sin la llave.",
        "entidades": [schemas.Referencia(tipo="personaje", id=creado.ilia)],
        "personajes_presentes": [creado.ilia],
        "consulta": vector(0.4, dimension),
    }
    campos.update(extra)
    return schemas.PeticionDeEnsamblado.model_validate(campos)


def consolidar_vacia(creado: Mundo) -> int:
    return creado.escena_consolidada(hechos=[])


__all__ = [
    "Capa",
    "Mundo",
    "NivelDeCompresion",
    "base_nueva",
    "canon",
    "canon_schemas",
    "consolidar_vacia",
    "indexar",
    "obra_indexada",
    "peticion",
    "umbrales",
    "vector",
]
