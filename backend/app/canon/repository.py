"""SQL explicito de `canon/`. Nadie de fuera de esta feature lo importa.

Toda escritura va en transaccion (RNF-02, A-17), y la consolidacion entera va en
**una sola**: toca hechos, snapshot, promesas y estado epistemico, y a medias
deja un canon que afirma cosas que el texto no dice.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.canon import models, schemas
from app.canon.models import TIPOS_DE_ESTADO, EstadoDePromesa, EstatusDeHecho, TipoDeHecho
from app.commons.db.conexion import Conexion, transaccion
from app.commons.errores import RecursoNoEncontrado

TABLAS_DEL_CANON = (
    "hecho_canonico",
    "snapshot_mundo",
    "hecho_snapshot",
    "estado_epistemico",
    "ironia_dramatica",
    "promesa_narrativa",
    "escena_promesa",
    "revelacion",
    "contradiccion",
    "retcon",
)

# Que hace de un hecho el sucesor de otro, por tipo. Es lo que decide a quien
# cierra un hecho nuevo: dos ubicaciones del mismo personaje se relevan; dos
# posesiones del mismo artefacto, tambien; dos descripciones, no.
CLAVE_DE_ESTADO: dict[TipoDeHecho, tuple[str, ...]] = {
    TipoDeHecho.ESTADO_VITAL: ("sujeto_personaje_id",),
    TipoDeHecho.UBICACION: ("sujeto_personaje_id",),
    TipoDeHecho.POSESION: ("artefacto_id",),
    TipoDeHecho.RELACION: ("sujeto_personaje_id", "objeto_personaje_id"),
}

VIGENTES = ("confirmado", "implicito", "provisional")


# --- Lecturas -------------------------------------------------------------


def posicion_de(base: Conexion, escena_id: int) -> int:
    fila = base.execute(
        "SELECT posicion FROM escena_ordenada WHERE escena_id = ?", (escena_id,)
    ).fetchone()
    if fila is None:
        raise RecursoNoEncontrado(f"la escena {escena_id} no esta en el orden del discurso")
    return int(fila["posicion"])


def inventario(base: Conexion) -> dict[str, int]:
    return {
        tabla: int(base.execute(f"SELECT COUNT(*) AS total FROM {tabla}").fetchone()["total"])
        for tabla in TABLAS_DEL_CANON
    }


def obtener_hecho(base: Conexion, hecho_id: int) -> models.HechoCanonico:
    fila = base.execute("SELECT * FROM hecho_canonico WHERE id = ?", (hecho_id,)).fetchone()
    if fila is None:
        raise RecursoNoEncontrado(f"no existe el hecho canonico {hecho_id}")
    return models.HechoCanonico.model_validate(dict(fila))


def obtener_promesa(base: Conexion, promesa_id: int) -> models.PromesaNarrativa:
    fila = base.execute("SELECT * FROM promesa_narrativa WHERE id = ?", (promesa_id,)).fetchone()
    if fila is None:
        raise RecursoNoEncontrado(f"no existe la promesa {promesa_id}")
    return models.PromesaNarrativa.model_validate(dict(fila))


def obtener_snapshot(base: Conexion, escena_id: int) -> models.SnapshotDeMundo | None:
    fila = base.execute("SELECT * FROM snapshot_mundo WHERE escena_id = ?", (escena_id,)).fetchone()
    return None if fila is None else models.SnapshotDeMundo.model_validate(dict(fila))


def hechos_establecidos_en(base: Conexion, escena_id: int) -> list[models.HechoCanonico]:
    return [
        models.HechoCanonico.model_validate(dict(fila))
        for fila in base.execute(
            "SELECT * FROM hecho_canonico WHERE escena_id = ? ORDER BY id", (escena_id,)
        )
    ]


def hechos_vigentes_en(base: Conexion, posicion: int) -> list[models.HechoCanonico]:
    """Hechos establecidos en `t` o antes y no cerrados todavia en `t`.

    P-48: un hecho con alcance abierto sigue vigente hasta que otro lo cierre.
    """
    marcadores = ", ".join("?" for _ in VIGENTES)
    filas = base.execute(
        f"""
        SELECT hecho.*
        FROM hecho_canonico AS hecho
        JOIN escena_ordenada AS inicio ON inicio.escena_id = hecho.escena_id
        LEFT JOIN escena_ordenada AS fin ON fin.escena_id = hecho.vigente_hasta_escena_id
        WHERE hecho.estatus IN ({marcadores})
          AND inicio.posicion <= ?
          AND (fin.posicion IS NULL OR fin.posicion > ?)
        ORDER BY inicio.posicion, hecho.id
        """,
        (*VIGENTES, posicion, posicion),
    )
    return [models.HechoCanonico.model_validate(dict(fila)) for fila in filas]


def epistemicos_de(
    base: Conexion, personaje_id: int, posicion: int
) -> list[models.EstadoEpistemico]:
    filas = base.execute(
        """
        SELECT epistemico.*
        FROM estado_epistemico AS epistemico
        JOIN escena_ordenada AS orden ON orden.escena_id = epistemico.escena_id
        WHERE epistemico.personaje_id = ? AND orden.posicion <= ?
        ORDER BY orden.posicion, epistemico.id
        """,
        (personaje_id, posicion),
    )
    return [models.EstadoEpistemico.model_validate(dict(fila)) for fila in filas]


def promesas_abiertas_en(base: Conexion, posicion: int) -> list[models.PromesaNarrativa]:
    filas = base.execute(
        """
        SELECT promesa.*
        FROM promesa_narrativa AS promesa
        JOIN escena_promesa AS apertura
          ON apertura.promesa_id = promesa.id AND apertura.rol = 'abre'
        JOIN escena_ordenada AS orden ON orden.escena_id = apertura.escena_id
        WHERE promesa.estado = 'pendiente' AND orden.posicion <= ?
        ORDER BY promesa.id
        """,
        (posicion,),
    )
    return [models.PromesaNarrativa.model_validate(dict(fila)) for fila in filas]


def escena_con_rol(base: Conexion, promesa_id: int, rol: str) -> int | None:
    fila = base.execute(
        "SELECT escena_id FROM escena_promesa WHERE promesa_id = ? AND rol = ?",
        (promesa_id, rol),
    ).fetchone()
    return None if fila is None else int(fila["escena_id"])


def ultima_escena_consolidada(base: Conexion) -> tuple[int, int] | None:
    fila = base.execute(
        """
        SELECT snapshot.escena_id AS escena_id, orden.posicion AS posicion
        FROM snapshot_mundo AS snapshot
        JOIN escena_ordenada AS orden ON orden.escena_id = snapshot.escena_id
        ORDER BY orden.posicion DESC LIMIT 1
        """
    ).fetchone()
    return None if fila is None else (int(fila["escena_id"]), int(fila["posicion"]))


def avances(base: Conexion, tabla: str) -> list[schemas.LineaDeAvance]:
    """Ultima posicion en la que cada arco o hilo avanzo. Cero si nunca avanzo."""
    sql = {
        "arco_escena": """
            SELECT arco.id AS id, arco.nombre AS nombre,
                   COALESCE(MAX(orden.posicion), 0) AS ultima
            FROM arco
            LEFT JOIN arco_escena AS puente ON puente.arco_id = arco.id
            LEFT JOIN escena_ordenada AS orden ON orden.escena_id = puente.escena_id
            GROUP BY arco.id ORDER BY arco.id
        """,
        "escena_hilo": """
            SELECT hilo.id AS id, hilo.nombre AS nombre,
                   COALESCE(MAX(orden.posicion), 0) AS ultima
            FROM hilo_de_trama AS hilo
            LEFT JOIN escena_hilo AS puente ON puente.hilo_id = hilo.id
            LEFT JOIN escena_ordenada AS orden ON orden.escena_id = puente.escena_id
            GROUP BY hilo.id ORDER BY hilo.id
        """,
    }[tabla]
    return [schemas.LineaDeAvance.model_validate(dict(fila)) for fila in base.execute(sql)]


def promesas_pendientes_con_apertura(base: Conexion) -> list[schemas.LineaDeAvance]:
    filas = base.execute(
        """
        SELECT promesa.id AS id, promesa.texto AS nombre, orden.posicion AS ultima
        FROM promesa_narrativa AS promesa
        JOIN escena_promesa AS apertura
          ON apertura.promesa_id = promesa.id AND apertura.rol = 'abre'
        JOIN escena_ordenada AS orden ON orden.escena_id = apertura.escena_id
        WHERE promesa.estado = 'pendiente'
        ORDER BY promesa.id
        """
    )
    return [schemas.LineaDeAvance.model_validate(dict(fila)) for fila in filas]


def escenas_que_tocan(base: Conexion, entidades: dict[str, int], desde: int) -> list[int]:
    """Escenas de `desde` en adelante con algun hecho sobre esas entidades.

    «Afectada» se calcula por las entidades del hecho retconeado. El punto ciego
    esta declarado en A-34 y se asume: una escena que dependia del hecho sin
    nombrar ninguna de sus entidades queda fuera y sobrevive.
    """
    if not entidades:
        return []
    condiciones = " OR ".join(f"hecho.{columna} = ?" for columna in entidades)
    filas = base.execute(
        f"""
        SELECT DISTINCT hecho.escena_id AS escena_id, orden.posicion AS posicion
        FROM hecho_canonico AS hecho
        JOIN escena_ordenada AS orden ON orden.escena_id = hecho.escena_id
        WHERE orden.posicion >= ? AND ({condiciones})
        ORDER BY orden.posicion
        """,
        (desde, *entidades.values()),
    )
    return [int(fila["escena_id"]) for fila in filas]


def formas_canonicas(base: Conexion) -> list[str]:
    return [str(fila["forma"]) for fila in base.execute("SELECT forma FROM termino_canonico")]


def nombres_de_entidades(base: Conexion, referencias: dict[str, int]) -> list[str]:
    """Nombre de cada entidad que un hecho referencia, para anclar en el texto."""
    consultas = {
        "sujeto_personaje_id": "SELECT nombre FROM personaje WHERE id = ?",
        "objeto_personaje_id": "SELECT nombre FROM personaje WHERE id = ?",
        "lugar_id": "SELECT nombre FROM lugar WHERE id = ?",
        "artefacto_id": "SELECT nombre FROM artefacto WHERE id = ?",
    }
    nombres: list[str] = []
    for columna, identificador in referencias.items():
        fila = base.execute(consultas[columna], (identificador,)).fetchone()
        if fila is not None:
            nombres.append(str(fila["nombre"]))
    return nombres


def revelaciones_pendientes(base: Conexion, posicion: int) -> list[schemas.RevelacionPendiente]:
    """Revelaciones cuya escena minima esta por delante de `t`.

    P-40: lo que todavia no se puede contar. Cubre las registradas; la que el
    borrador filtra sin que nadie la haya registrado se queda fuera.
    """
    return [
        schemas.RevelacionPendiente.model_validate(dict(fila))
        for fila in base.execute(
            """
            SELECT revelacion.hecho_id AS hecho_id, hecho.texto AS texto,
                   hecho.valor AS valor, minima.posicion AS escena_minima
            FROM revelacion
            JOIN hecho_canonico AS hecho ON hecho.id = revelacion.hecho_id
            JOIN escena_ordenada AS minima ON minima.escena_id = revelacion.escena_minima_id
            WHERE minima.posicion > ?
            """,
            (posicion,),
        )
    ]


def contradicciones(base: Conexion) -> list[models.Contradiccion]:
    return [
        models.Contradiccion.model_validate(dict(fila))
        for fila in base.execute("SELECT * FROM contradiccion ORDER BY id")
    ]


# --- Escrituras -----------------------------------------------------------


def escribir_consolidacion(
    base: Conexion, datos: schemas.Consolidacion, posicion: int
) -> schemas.ResultadoDeConsolidacion:
    """Todo el canon de una escena, en una sola transaccion (RF-CANON-08).

    Si algo falla, no entra nada: a medias, el canon afirmaria cosas que el
    texto no dice.
    """
    with transaccion(base):
        # Sustituir lo que dejo una version anterior de esta misma escena. Sin
        # esto, reescribir una escena acumula su canon viejo y el nuevo.
        base.execute("DELETE FROM hecho_canonico WHERE escena_id = ?", (datos.escena_id,))
        base.execute("DELETE FROM escena_promesa WHERE escena_id = ?", (datos.escena_id,))
        base.execute(
            "DELETE FROM promesa_narrativa WHERE id NOT IN (SELECT promesa_id FROM escena_promesa)"
        )
        base.execute("DELETE FROM snapshot_mundo WHERE escena_id = ?", (datos.escena_id,))

        cursor = base.execute(
            "INSERT INTO snapshot_mundo (escena_id, version, fecha_ficcional, consolidado_en) "
            "VALUES (:escena_id, :version, :fecha_ficcional, :consolidado_en)",
            {
                "escena_id": datos.escena_id,
                "version": datos.version,
                "fecha_ficcional": datos.fecha_ficcional,
                "consolidado_en": datetime.now(UTC).isoformat(),
            },
        )
        snapshot_id = cursor.lastrowid
        assert snapshot_id is not None

        hechos: list[int] = []
        for nuevo in datos.hechos:
            cursor = base.execute(
                "INSERT INTO hecho_canonico (texto, tipo, escena_id, estatus, "
                "sujeto_personaje_id, objeto_personaje_id, lugar_id, artefacto_id, valor, "
                "sucede_a_hecho_id) "
                "VALUES (:texto, :tipo, :escena_id, :estatus, :sujeto_personaje_id, "
                ":objeto_personaje_id, :lugar_id, :artefacto_id, :valor, :sucede_a_hecho_id)",
                {**nuevo.model_dump(), "escena_id": datos.escena_id},
            )
            hecho_id = cursor.lastrowid
            assert hecho_id is not None
            hechos.append(hecho_id)
            base.execute(
                "INSERT INTO hecho_snapshot (hecho_id, snapshot_id) VALUES (?, ?)",
                (hecho_id, snapshot_id),
            )
            if nuevo.tipo in TIPOS_DE_ESTADO:
                _cerrar_los_anteriores(base, nuevo, hecho_id, datos.escena_id, posicion)

        promesas: list[int] = []
        for promesa in datos.promesas:
            cursor = base.execute(
                "INSERT INTO promesa_narrativa (texto, tipo, estado, artefacto_id) "
                "VALUES (:texto, :tipo, 'pendiente', :artefacto_id)",
                promesa.model_dump(),
            )
            promesa_id = cursor.lastrowid
            assert promesa_id is not None
            promesas.append(promesa_id)
            base.execute(
                "INSERT INTO escena_promesa (escena_id, promesa_id, rol) VALUES (?, ?, 'abre')",
                (datos.escena_id, promesa_id),
            )

        for revelacion in datos.revelaciones:
            base.execute(
                "INSERT INTO revelacion (hecho_id, destinatario, personaje_id, "
                "escena_minima_id) VALUES (:hecho_id, :destinatario, :personaje_id, "
                ":escena_minima_id)",
                revelacion.model_dump(),
            )

        epistemicos: list[int] = []
        for epistemico in datos.epistemicos:
            hecho_id = (
                epistemico.hecho_id
                if epistemico.hecho_id is not None
                else hechos[epistemico.indice_del_hecho or 0]
            )
            cursor = base.execute(
                "INSERT INTO estado_epistemico (personaje_id, hecho_id, escena_id, certeza) "
                "VALUES (?, ?, ?, ?)",
                (epistemico.personaje_id, hecho_id, datos.escena_id, epistemico.certeza),
            )
            identificador = cursor.lastrowid
            assert identificador is not None
            epistemicos.append(identificador)

    snapshot = obtener_snapshot(base, datos.escena_id)
    assert snapshot is not None
    return schemas.ResultadoDeConsolidacion(
        snapshot=snapshot,
        hechos=[obtener_hecho(base, identificador) for identificador in hechos],
        promesas=[obtener_promesa(base, identificador) for identificador in promesas],
        epistemicos=[_obtener_epistemico(base, identificador) for identificador in epistemicos],
    )


def _cerrar_los_anteriores(
    base: Conexion,
    nuevo: schemas.NuevoHechoCanonico,
    hecho_id: int,
    escena_id: int,
    posicion: int,
) -> None:
    """P-48: el hecho nuevo cierra el alcance abierto del que releva."""
    columnas = CLAVE_DE_ESTADO[nuevo.tipo]
    valores = [getattr(nuevo, columna) for columna in columnas]
    if any(valor is None for valor in valores):
        return
    filtro = " AND ".join(f"{columna} = ?" for columna in columnas)
    base.execute(
        f"""
        UPDATE hecho_canonico
        SET vigente_hasta_escena_id = ?, cerrado_por_hecho_id = ?
        WHERE tipo = ? AND {filtro}
          AND vigente_hasta_escena_id IS NULL
          AND id <> ?
          AND escena_id IN (SELECT escena_id FROM escena_ordenada WHERE posicion < ?)
        """,
        (escena_id, hecho_id, nuevo.tipo.value, *valores, hecho_id, posicion),
    )


def _obtener_epistemico(base: Conexion, identificador: int) -> models.EstadoEpistemico:
    fila = base.execute("SELECT * FROM estado_epistemico WHERE id = ?", (identificador,)).fetchone()
    if fila is None:
        raise RecursoNoEncontrado(f"no existe el estado epistemico {identificador}")
    return models.EstadoEpistemico.model_validate(dict(fila))


def actualizar_estatus_de_hecho(
    base: Conexion, hecho_id: int, destino: EstatusDeHecho
) -> models.HechoCanonico:
    with transaccion(base):
        base.execute(
            "UPDATE hecho_canonico SET estatus = ? WHERE id = ?", (destino.value, hecho_id)
        )
    return obtener_hecho(base, hecho_id)


def actualizar_estado_de_promesa(
    base: Conexion, promesa_id: int, destino: EstadoDePromesa, escena_de_pago_id: int | None
) -> models.PromesaNarrativa:
    with transaccion(base):
        base.execute(
            "UPDATE promesa_narrativa SET estado = ? WHERE id = ?", (destino.value, promesa_id)
        )
        if escena_de_pago_id is not None:
            base.execute(
                "INSERT OR REPLACE INTO escena_promesa (escena_id, promesa_id, rol) "
                "VALUES (?, ?, 'paga')",
                (escena_de_pago_id, promesa_id),
            )
    return obtener_promesa(base, promesa_id)


def registrar_contradiccion(
    base: Conexion, hecho_a_id: int, hecho_b_id: int, tipo: str, gravedad: str
) -> None:
    with transaccion(base):
        ya_esta = base.execute(
            "SELECT 1 FROM contradiccion WHERE hecho_a_id = ? AND hecho_b_id = ?",
            (hecho_a_id, hecho_b_id),
        ).fetchone()
        if ya_esta is None:
            base.execute(
                "INSERT INTO contradiccion (hecho_a_id, hecho_b_id, tipo, gravedad) "
                "VALUES (?, ?, ?, ?)",
                (hecho_a_id, hecho_b_id, tipo, gravedad),
            )
