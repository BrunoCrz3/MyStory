"""SQL explicito de `quality/`."""

from __future__ import annotations

from datetime import UTC, datetime

from app.commons.db.conexion import Conexion, transaccion
from app.commons.errores import RecursoNoEncontrado
from app.quality import models, schemas
from app.quality.models import AlcanceDelDefecto, DimensionDeCalidad, Eje


def dimensiones(base: Conexion) -> list[DimensionDeCalidad]:
    return [
        DimensionDeCalidad.model_validate(dict(fila))
        for fila in base.execute("SELECT * FROM dimension_calidad ORDER BY id")
    ]


def escenas_aceptadas(base: Conexion) -> int:
    fila = base.execute("SELECT COUNT(*) AS total FROM escena WHERE estado = 'aceptada'").fetchone()
    return int(fila["total"])


def guardar_informe(
    base: Conexion,
    peticion: schemas.PeticionDeCritica,
    fase_de_medicion: bool,
    aceptadas: int,
    puntuaciones: list[schemas.Puntuacion],
    defectos: list[tuple[schemas.DefectoDetectado, AlcanceDelDefecto]],
) -> int:
    """El informe entero en una transaccion: o esta completo o no esta."""
    por_nombre = {dimension.nombre: dimension.id for dimension in dimensiones(base)}

    with transaccion(base):
        base.execute(
            "DELETE FROM informe_critica WHERE escena_id = ? AND version = ?",
            (peticion.escena_id, peticion.version),
        )
        cursor = base.execute(
            "INSERT INTO informe_critica (escena_id, version, fase_de_medicion, "
            "escenas_aceptadas, emitido_en) VALUES (?, ?, ?, ?, ?)",
            (
                peticion.escena_id,
                peticion.version,
                int(fase_de_medicion),
                aceptadas,
                datetime.now(UTC).isoformat(),
            ),
        )
        informe_id = cursor.lastrowid
        assert informe_id is not None

        for puntuacion in puntuaciones:
            base.execute(
                "INSERT INTO puntuacion_de_dimension (informe_id, dimension_id, valor, "
                "umbral, suspende, motivo) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    informe_id,
                    por_nombre[puntuacion.dimension],
                    puntuacion.valor,
                    puntuacion.umbral,
                    int(puntuacion.suspende),
                    puntuacion.motivo,
                ),
            )

        for detectado, alcance in defectos:
            base.execute(
                "INSERT INTO defecto (informe_id, dimension_id, gravedad, alcance, eje, "
                "localizacion, descripcion) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    informe_id,
                    por_nombre[detectado.dimension],
                    detectado.gravedad,
                    alcance.value,
                    detectado.eje.value if detectado.eje else None,
                    detectado.localizacion,
                    detectado.descripcion,
                ),
            )
    return informe_id


def obtener_informe(base: Conexion, informe_id: int) -> models.InformeDeCritica:
    fila = base.execute("SELECT * FROM informe_critica WHERE id = ?", (informe_id,)).fetchone()
    if fila is None:
        raise RecursoNoEncontrado(f"no existe el informe de critica {informe_id}")
    return _a_informe(fila)


def informes_de(base: Conexion, escena_id: int) -> list[models.InformeDeCritica]:
    return [
        _a_informe(fila)
        for fila in base.execute(
            "SELECT * FROM informe_critica WHERE escena_id = ? ORDER BY version",
            (escena_id,),
        )
    ]


def puntuaciones_de(base: Conexion, informe_id: int) -> list[schemas.Puntuacion]:
    return [
        schemas.Puntuacion(
            dimension=str(fila["nombre"]),
            valor=fila["valor"],
            umbral=fila["umbral"],
            suspende=bool(fila["suspende"]),
            motivo=fila["motivo"],
        )
        for fila in base.execute(
            "SELECT dimension_calidad.nombre AS nombre, puntuacion_de_dimension.* "
            "FROM puntuacion_de_dimension "
            "JOIN dimension_calidad ON dimension_calidad.id = "
            "puntuacion_de_dimension.dimension_id "
            "WHERE puntuacion_de_dimension.informe_id = ? ORDER BY dimension_calidad.id",
            (informe_id,),
        )
    ]


def defectos_de(base: Conexion, informe_id: int) -> list[models.Defecto]:
    return [
        models.Defecto(
            id=int(fila["id"]),
            informe_id=int(fila["informe_id"]),
            dimension=str(fila["nombre"]),
            gravedad=str(fila["gravedad"]),
            alcance=AlcanceDelDefecto(fila["alcance"]),
            eje=Eje(fila["eje"]) if fila["eje"] else None,
            localizacion=fila["localizacion"],
            descripcion=str(fila["descripcion"]),
        )
        for fila in base.execute(
            "SELECT defecto.*, dimension_calidad.nombre AS nombre FROM defecto "
            "JOIN dimension_calidad ON dimension_calidad.id = defecto.dimension_id "
            "WHERE defecto.informe_id = ? ORDER BY defecto.id",
            (informe_id,),
        )
    ]


def informe_anterior(
    base: Conexion, escena_id: int, version: int
) -> models.InformeDeCritica | None:
    fila = base.execute(
        "SELECT * FROM informe_critica WHERE escena_id = ? AND version < ? "
        "ORDER BY version DESC LIMIT 1",
        (escena_id, version),
    ).fetchone()
    return None if fila is None else _a_informe(fila)


def informe_de(base: Conexion, escena_id: int, version: int) -> models.InformeDeCritica | None:
    fila = base.execute(
        "SELECT * FROM informe_critica WHERE escena_id = ? AND version = ?",
        (escena_id, version),
    ).fetchone()
    return None if fila is None else _a_informe(fila)


def _a_informe(fila: object) -> models.InformeDeCritica:
    datos = dict(fila)  # type: ignore[call-overload]
    datos["fase_de_medicion"] = bool(datos["fase_de_medicion"])
    return models.InformeDeCritica.model_validate(datos)
