"""SQL explicito de `novel/`. No lo importa nadie de fuera de esta feature.

El `INSERT` de cada entidad lleva sus columnas escritas: es donde un despiste
cuesta caro y donde conviene poder leer, de un vistazo, que se guarda. Las
lecturas comparten dos ayudas porque la unica variable es la tabla y el modelo,
y repetir `SELECT * FROM x WHERE id = ?` veinte veces no documenta nada.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.commons.db.conexion import Conexion, transaccion
from app.commons.errores import ConflictoDeEstado, RecursoNoEncontrado
from app.novel import models, schemas

# Nombre de tabla por modelo. Lo usa la lectura generica; los nombres son
# literales de este modulo, nunca entrada del usuario.
TABLAS: dict[type[models.Entidad], str] = {
    models.Obra: "obra",
    models.Parte: "parte",
    models.Capitulo: "capitulo",
    models.Escena: "escena",
    models.Beat: "beat",
    models.Personaje: "personaje",
    models.Voz: "voz",
    models.Arco: "arco",
    models.HiloDeTrama: "hilo_de_trama",
    models.Lugar: "lugar",
    models.Faccion: "faccion",
    models.Artefacto: "artefacto",
    models.Novum: "novum",
    models.ReglaDelMundo: "regla_del_mundo",
    models.TerminoCanonico: "termino_canonico",
    models.Tema: "tema",
    models.Motivo: "motivo",
    models.VozNarrativa: "voz_narrativa",
    models.Evento: "evento",
    models.Objetivo: "objetivo",
}


def obtener[E: models.Entidad](base: Conexion, modelo: type[E], identificador: int) -> E:
    tabla = TABLAS[modelo]
    fila = base.execute(f"SELECT * FROM {tabla} WHERE id = ?", (identificador,)).fetchone()
    if fila is None:
        raise RecursoNoEncontrado(f"no existe {tabla} con id {identificador}")
    return modelo.model_validate(dict(fila))


def listar[E: models.Entidad](base: Conexion, modelo: type[E]) -> list[E]:
    tabla = TABLAS[modelo]
    return [
        modelo.model_validate(dict(fila))
        for fila in base.execute(f"SELECT * FROM {tabla} ORDER BY id")
    ]


def _insertar[E: models.Entidad](
    base: Conexion, sql: str, datos: dict[str, Any], modelo: type[E]
) -> E:
    with transaccion(base):
        cursor = _ejecutar(base, sql, datos)
        identificador = cursor.lastrowid
    assert identificador is not None
    return obtener(base, modelo, identificador)


def _ejecutar(base: Conexion, sql: str, datos: dict[str, Any]) -> sqlite3.Cursor:
    """Traduce la integridad del esquema a un error de dominio.

    Una clave foranea rota o un `unique` violado no son un fallo del servidor:
    son una peticion que contradice la obra. Salen por el handler central como
    conflicto, no como 500 (RI-04).
    """
    try:
        return base.execute(sql, datos)
    except sqlite3.IntegrityError as error:
        raise ConflictoDeEstado(str(error), codigo="integridad_violada") from error


# --- Arbol estructural ----------------------------------------------------


def insertar_obra(base: Conexion, datos: schemas.NuevaObra) -> models.Obra:
    # Una sola obra por instancia: la clave va fijada a 1 y el CHECK de la
    # migracion 001 impide una segunda.
    return _insertar(
        base,
        "INSERT INTO obra (id, titulo, premisa, genero, extension_objetivo, publico) "
        "VALUES (1, :titulo, :premisa, :genero, :extension_objetivo, :publico)",
        datos.model_dump(),
        models.Obra,
    )


def obtener_la_obra(base: Conexion) -> models.Obra:
    fila = base.execute("SELECT * FROM obra WHERE id = 1").fetchone()
    if fila is None:
        raise RecursoNoEncontrado("todavia no hay obra en esta instancia")
    return models.Obra.model_validate(dict(fila))


def insertar_parte(base: Conexion, datos: schemas.NuevaParte) -> models.Parte:
    return _insertar(
        base,
        "INSERT INTO parte (obra_id, orden, funcion_dramatica, punto_de_giro) "
        "VALUES (:obra_id, :orden, :funcion_dramatica, :punto_de_giro)",
        datos.model_dump(),
        models.Parte,
    )


def insertar_capitulo(base: Conexion, datos: schemas.NuevoCapitulo) -> models.Capitulo:
    return _insertar(
        base,
        "INSERT INTO capitulo (parte_id, orden, pov_dominante_id, gancho_de_cierre) "
        "VALUES (:parte_id, :orden, :pov_dominante_id, :gancho_de_cierre)",
        datos.model_dump(),
        models.Capitulo,
    )


def insertar_escena(base: Conexion, datos: schemas.NuevaEscena) -> models.Escena:
    return _insertar(
        base,
        "INSERT INTO escena (capitulo_id, orden, objetivo, conflicto, resultado, "
        "personaje_pov_id, lugar_id, momento, estado_de_entrada, estado_de_salida) "
        "VALUES (:capitulo_id, :orden, :objetivo, :conflicto, :resultado, "
        ":personaje_pov_id, :lugar_id, :momento, :estado_de_entrada, :estado_de_salida)",
        datos.model_dump(),
        models.Escena,
    )


def actualizar_estado_de_escena(
    base: Conexion, escena_id: int, destino: models.EstadoDeEscena
) -> models.Escena:
    with transaccion(base):
        _ejecutar(
            base,
            "UPDATE escena SET estado = :estado WHERE id = :id",
            {"estado": destino.value, "id": escena_id},
        )
    return obtener(base, models.Escena, escena_id)


def actualizar_estado_de_hilo(
    base: Conexion, hilo_id: int, destino: models.EstadoDeHilo
) -> models.HiloDeTrama:
    with transaccion(base):
        _ejecutar(
            base,
            "UPDATE hilo_de_trama SET estado = :estado WHERE id = :id",
            {"estado": destino.value, "id": hilo_id},
        )
    return obtener(base, models.HiloDeTrama, hilo_id)


def insertar_beat(base: Conexion, datos: schemas.NuevoBeat) -> models.Beat:
    return _insertar(
        base,
        "INSERT INTO beat (escena_id, orden, valor_inicial, valor_final) "
        "VALUES (:escena_id, :orden, :valor_inicial, :valor_final)",
        datos.model_dump(),
        models.Beat,
    )


# --- Entidades narrativas -------------------------------------------------


def insertar_personaje(base: Conexion, datos: schemas.NuevoPersonaje) -> models.Personaje:
    return _insertar(
        base,
        "INSERT INTO personaje (nombre, deseo, necesidad, herida, rol_narrativo, arco_id) "
        "VALUES (:nombre, :deseo, :necesidad, :herida, :rol_narrativo, :arco_id)",
        datos.model_dump(),
        models.Personaje,
    )


def insertar_voz(base: Conexion, datos: schemas.NuevaVoz) -> models.Voz:
    return _insertar(
        base,
        "INSERT INTO voz (personaje_id, lexico, registro, sintaxis, muletillas, "
        "temas_recurrentes) VALUES (:personaje_id, :lexico, :registro, :sintaxis, "
        ":muletillas, :temas_recurrentes)",
        datos.model_dump(),
        models.Voz,
    )


def insertar_arco(base: Conexion, datos: schemas.NuevoArco) -> models.Arco:
    return _insertar(
        base,
        "INSERT INTO arco (nombre, estado_inicial, puntos_de_giro, estado_final) "
        "VALUES (:nombre, :estado_inicial, :puntos_de_giro, :estado_final)",
        datos.model_dump(),
        models.Arco,
    )


def insertar_hilo_de_trama(base: Conexion, datos: schemas.NuevoHiloDeTrama) -> models.HiloDeTrama:
    return _insertar(
        base,
        "INSERT INTO hilo_de_trama (nombre, tipo, pregunta_dramatica, estado) "
        "VALUES (:nombre, :tipo, :pregunta_dramatica, :estado)",
        datos.model_dump(),
        models.HiloDeTrama,
    )


def insertar_lugar(base: Conexion, datos: schemas.NuevoLugar) -> models.Lugar:
    return _insertar(
        base,
        "INSERT INTO lugar (nombre, geografia, atmosfera_sensorial, reglas_propias) "
        "VALUES (:nombre, :geografia, :atmosfera_sensorial, :reglas_propias)",
        datos.model_dump(),
        models.Lugar,
    )


def insertar_faccion(base: Conexion, datos: schemas.NuevaFaccion) -> models.Faccion:
    return _insertar(
        base,
        "INSERT INTO faccion (nombre, objetivo, recursos) VALUES (:nombre, :objetivo, :recursos)",
        datos.model_dump(),
        models.Faccion,
    )


def insertar_artefacto(base: Conexion, datos: schemas.NuevoArtefacto) -> models.Artefacto:
    return _insertar(
        base,
        "INSERT INTO artefacto (nombre, propiedades, poseedor_actual_id, deuda_narrativa) "
        "VALUES (:nombre, :propiedades, :poseedor_actual_id, :deuda_narrativa)",
        datos.model_dump(),
        models.Artefacto,
    )


def insertar_novum(base: Conexion, datos: schemas.NuevoNovum) -> models.Novum:
    return _insertar(
        base,
        "INSERT INTO novum (nombre, mecanismo, limites, consecuencias_en_cascada) "
        "VALUES (:nombre, :mecanismo, :limites, :consecuencias_en_cascada)",
        datos.model_dump(),
        models.Novum,
    )


def insertar_regla_del_mundo(
    base: Conexion, datos: schemas.NuevaReglaDelMundo
) -> models.ReglaDelMundo:
    return _insertar(
        base,
        "INSERT INTO regla_del_mundo (novum_id, enunciado, alcance, excepciones_declaradas) "
        "VALUES (:novum_id, :enunciado, :alcance, :excepciones_declaradas)",
        datos.model_dump(),
        models.ReglaDelMundo,
    )


def contar_reglas_del_novum(base: Conexion, novum_id: int) -> int:
    fila = base.execute(
        "SELECT COUNT(*) AS total FROM regla_del_mundo WHERE novum_id = ?", (novum_id,)
    ).fetchone()
    return int(fila["total"])


def insertar_termino_canonico(
    base: Conexion, datos: schemas.NuevoTerminoCanonico
) -> models.TerminoCanonico:
    return _insertar(
        base,
        "INSERT INTO termino_canonico (forma, definicion, novum_id, primera_aparicion_id, "
        "variantes_prohibidas) VALUES (:forma, :definicion, :novum_id, "
        ":primera_aparicion_id, :variantes_prohibidas)",
        datos.model_dump(),
        models.TerminoCanonico,
    )


def insertar_tema(base: Conexion, datos: schemas.NuevoTema) -> models.Tema:
    return _insertar(
        base,
        "INSERT INTO tema (nombre, enunciado) VALUES (:nombre, :enunciado)",
        datos.model_dump(),
        models.Tema,
    )


def insertar_motivo(base: Conexion, datos: schemas.NuevoMotivo) -> models.Motivo:
    return _insertar(
        base,
        "INSERT INTO motivo (nombre, forma, evolucion) VALUES (:nombre, :forma, :evolucion)",
        datos.model_dump(),
        models.Motivo,
    )


def insertar_voz_narrativa(base: Conexion, datos: schemas.NuevaVozNarrativa) -> models.VozNarrativa:
    return _insertar(
        base,
        "INSERT INTO voz_narrativa (obra_id, persona, tiempo_verbal, distancia, focalizacion, "
        "ratio_escena_resumen) VALUES (:obra_id, :persona, :tiempo_verbal, :distancia, "
        ":focalizacion, :ratio_escena_resumen)",
        datos.model_dump(),
        models.VozNarrativa,
    )


def insertar_evento(base: Conexion, datos: schemas.NuevoEvento) -> models.Evento:
    return _insertar(
        base,
        "INSERT INTO evento (que_ocurre, momento_en_la_fabula, duracion) "
        "VALUES (:que_ocurre, :momento_en_la_fabula, :duracion)",
        datos.model_dump(),
        models.Evento,
    )


def insertar_objetivo(base: Conexion, datos: schemas.NuevoObjetivo) -> models.Objetivo:
    return _insertar(
        base,
        "INSERT INTO objetivo (personaje_id, enunciado, alcance, tipo, estado) "
        "VALUES (:personaje_id, :enunciado, :alcance, :tipo, :estado)",
        datos.model_dump(),
        models.Objetivo,
    )


# --- Puente `Evento se narra en Escena` -----------------------------------


def enlazar_evento_con_escena(base: Conexion, evento_id: int, escena_id: int) -> None:
    """Idempotente, y sin `INSERT OR IGNORE`.

    `OR IGNORE` tambien se traga una clave foranea rota, que es justo el punto
    ciego que `verification.md` anota en A-20: la restriccion queda declarada y
    el codigo la esquiva. Se comprueba la existencia y se inserta de verdad.
    """
    parametros = {"evento_id": evento_id, "escena_id": escena_id}
    with transaccion(base):
        ya_esta = base.execute(
            "SELECT 1 FROM evento_escena WHERE evento_id = :evento_id AND escena_id = :escena_id",
            parametros,
        ).fetchone()
        if ya_esta is None:
            _ejecutar(
                base,
                "INSERT INTO evento_escena (evento_id, escena_id) VALUES (:evento_id, :escena_id)",
                parametros,
            )


def escenas_donde_se_narra(base: Conexion, evento_id: int) -> list[models.Escena]:
    return [
        models.Escena.model_validate(dict(fila))
        for fila in base.execute(
            "SELECT escena.* FROM escena "
            "JOIN evento_escena ON evento_escena.escena_id = escena.id "
            "WHERE evento_escena.evento_id = ? ORDER BY escena.id",
            (evento_id,),
        )
    ]
