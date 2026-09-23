"""SQL explicito de `findings/`.

Escribe sus dos tablas y nada mas. En particular **no escribe el canon**: un
hallazgo adoptado apunta al hecho o a la promesa que el autor eligio, y quien
los creo fue `canon/` al consolidar. Si esto escribiera canon habria dos puntos
de promocion a memoria larga, que es justo lo que RF-FIND-04 prohibe.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.commons.db.conexion import Conexion, transaccion
from app.commons.errores import RecursoNoEncontrado
from app.findings import schemas
from app.findings.models import (
    EstadoDeHallazgo,
    Extraccion,
    FuenteDelHallazgo,
    Hallazgo,
    TipoDeHallazgo,
)


def ahora() -> str:
    return datetime.now(UTC).isoformat()


def extraccion_de(base: Conexion, escena_id: int, version: int) -> Extraccion | None:
    fila = base.execute(
        "SELECT * FROM extraccion WHERE escena_id = ? AND version = ?", (escena_id, version)
    ).fetchone()
    return None if fila is None else Extraccion.model_validate(dict(fila))


def guardar_extraccion(
    base: Conexion,
    escena_id: int,
    version: int,
    entradas: str,
    registro_id: int | None,
    propuestas: list[tuple[TipoDeHallazgo, str, FuenteDelHallazgo, float | None]],
) -> Extraccion:
    """La extraccion y sus hallazgos, en una transaccion.

    O estan todos o no esta ninguno: media bandeja de propuestas es peor que
    ninguna, porque el autor no sabe que le falta la otra mitad.
    """
    with transaccion(base):
        cursor = base.execute(
            "INSERT INTO extraccion (escena_id, version, entradas, confianza, registro_id, "
            "extraido_en) VALUES (?, ?, ?, ?, ?, ?)",
            (escena_id, version, entradas, None, registro_id, ahora()),
        )
        extraccion_id = cursor.lastrowid
        assert extraccion_id is not None
        for tipo, texto, fuente, confianza in propuestas:
            base.execute(
                "INSERT OR IGNORE INTO hallazgo (extraccion_id, escena_id, tipo, texto, "
                "fuente, confianza, propuesto_en) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (extraccion_id, escena_id, tipo.value, texto, fuente.value, confianza, ahora()),
            )
    return obtener_extraccion(base, extraccion_id)


def obtener_extraccion(base: Conexion, extraccion_id: int) -> Extraccion:
    fila = base.execute("SELECT * FROM extraccion WHERE id = ?", (extraccion_id,)).fetchone()
    if fila is None:
        raise RecursoNoEncontrado(f"no existe la extraccion {extraccion_id}")
    return Extraccion.model_validate(dict(fila))


def obtener_hallazgo(base: Conexion, hallazgo_id: int) -> Hallazgo:
    fila = base.execute("SELECT * FROM hallazgo WHERE id = ?", (hallazgo_id,)).fetchone()
    if fila is None:
        raise RecursoNoEncontrado(f"no existe el hallazgo {hallazgo_id}")
    return Hallazgo.model_validate(dict(fila))


def hallazgos_de_la_extraccion(base: Conexion, extraccion_id: int) -> list[Hallazgo]:
    return [
        Hallazgo.model_validate(dict(fila))
        for fila in base.execute(
            "SELECT * FROM hallazgo WHERE extraccion_id = ? ORDER BY id", (extraccion_id,)
        )
    ]


def hallazgos_de_la_escena(base: Conexion, escena_id: int) -> list[Hallazgo]:
    return [
        Hallazgo.model_validate(dict(fila))
        for fila in base.execute(
            "SELECT * FROM hallazgo WHERE escena_id = ? ORDER BY id", (escena_id,)
        )
    ]


def hallazgos_en(base: Conexion, estado: EstadoDeHallazgo) -> list[Hallazgo]:
    return [
        Hallazgo.model_validate(dict(fila))
        for fila in base.execute(
            "SELECT * FROM hallazgo WHERE estado = ? ORDER BY id", (estado.value,)
        )
    ]


def adoptados_desde(base: Conexion, posicion: int) -> list[Hallazgo]:
    """Los que ya son verdad de la novela y se adoptaron a partir de `posicion`.

    Es lo que `canon_huerfano` cuenta del modo hibrido. Se ordena por discurso
    porque la deriva es una serie, no un conjunto.
    """
    return [
        Hallazgo.model_validate(dict(fila))
        for fila in base.execute(
            """
            SELECT hallazgo.* FROM hallazgo
            JOIN escena_ordenada AS orden ON orden.escena_id = hallazgo.escena_id
            WHERE hallazgo.estado IN ('adoptado', 'integrado') AND orden.posicion > ?
            ORDER BY orden.posicion, hallazgo.id
            """,
            (posicion,),
        )
    ]


def adoptados(base: Conexion) -> list[Hallazgo]:
    return [
        Hallazgo.model_validate(dict(fila))
        for fila in base.execute(
            "SELECT * FROM hallazgo WHERE estado IN ('adoptado', 'integrado') ORDER BY id"
        )
    ]


def actualizar_estado(
    base: Conexion,
    hallazgo_id: int,
    destino: EstadoDeHallazgo,
    decision: schemas.DecisionDelAutor,
) -> Hallazgo:
    with transaccion(base):
        base.execute(
            "UPDATE hallazgo SET estado = :estado, hecho_id = COALESCE(:hecho_id, hecho_id), "
            "promesa_id = COALESCE(:promesa_id, promesa_id), "
            "motivo_id = COALESCE(:motivo_id, motivo_id), "
            "personaje_id = COALESCE(:personaje_id, personaje_id), "
            "decidido_por = 'autor_humano', decidido_en = :decidido_en WHERE id = :id",
            {
                "estado": destino.value,
                "hecho_id": decision.hecho_id,
                "promesa_id": decision.promesa_id,
                "motivo_id": decision.motivo_id,
                "personaje_id": decision.personaje_id,
                "decidido_en": ahora(),
                "id": hallazgo_id,
            },
        )
    return obtener_hallazgo(base, hallazgo_id)
