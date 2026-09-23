"""SQL explicito de `process/`.

Lee tablas de `novel/` y usa la vista `escena_ordenada` de `canon/`, y las dos
cosas son lecturas: la regla que `AGENTS.md` cierra es que una feature no importe
el `repository.py` de otra, y que solo `canon/` **escriba** el canon. Aqui no se
escribe ni una fila fuera de las tablas de la migracion 006.

`escena_ordenada` es el unico sitio donde se decide que escena viene primero, y
por eso toda cuenta que dependa de «antes» o «despues» pasa por ella en vez de
ordenar por `id`: los `id` son de insercion, no de discurso.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.commons.db.conexion import Conexion, transaccion
from app.commons.errores import RecursoNoEncontrado
from app.process import models, schemas
from app.process.models import (
    Borrador,
    BriefDeEscena,
    Deriva,
    Esquema,
    OrigenDeVersion,
    RegistroDeGeneracion,
    RestriccionDeDestino,
    Version,
)

# Estado de una escena todavia por escribir. `obsoleta` no cuenta: el diagrama la
# devuelve a `planificada`, asi que su paso por aqui es de ida y vuelta.
POR_ESCRIBIR = "planificada"


def ahora() -> str:
    return datetime.now(UTC).isoformat()


# --- Lecturas sobre el discurso -------------------------------------------


def posicion_de(base: Conexion, escena_id: int) -> int:
    fila = base.execute(
        "SELECT posicion FROM escena_ordenada WHERE escena_id = ?", (escena_id,)
    ).fetchone()
    if fila is None:
        raise RecursoNoEncontrado(f"no existe la escena {escena_id}")
    return int(fila["posicion"])


def ultima_posicion_aceptada(base: Conexion) -> int:
    """Donde esta el discurso ahora mismo. Cero si no hay ninguna aceptada."""
    fila = base.execute(
        """
        SELECT COALESCE(MAX(orden.posicion), 0) AS posicion
        FROM escena
        JOIN escena_ordenada AS orden ON orden.escena_id = escena.id
        WHERE escena.estado = 'aceptada'
        """
    ).fetchone()
    return int(fila["posicion"])


def contar_escenas_planificadas(base: Conexion) -> int:
    fila = base.execute(
        "SELECT COUNT(*) AS total FROM escena WHERE estado = ?", (POR_ESCRIBIR,)
    ).fetchone()
    return int(fila["total"])


def apertura_de_hilo(base: Conexion, hilo_id: int) -> int:
    """Primera escena en la que el hilo avanza. Cero si aun no avanzo en ninguna.

    Cero lo deja siempre por delante de cualquier hito: un hilo declarado y
    todavia sin narrar es parte del plan, no canon que el plan no recogiera.
    """
    fila = base.execute(
        """
        SELECT COALESCE(MIN(orden.posicion), 0) AS posicion
        FROM escena_hilo AS puente
        JOIN escena_ordenada AS orden ON orden.escena_id = puente.escena_id
        WHERE puente.hilo_id = ?
        """,
        (hilo_id,),
    ).fetchone()
    return int(fila["posicion"])


def apertura_de_promesa(base: Conexion, promesa_id: int) -> int:
    fila = base.execute(
        """
        SELECT COALESCE(MIN(orden.posicion), 0) AS posicion
        FROM escena_promesa AS puente
        JOIN escena_ordenada AS orden ON orden.escena_id = puente.escena_id
        WHERE puente.promesa_id = ? AND puente.rol = 'abre'
        """,
        (promesa_id,),
    ).fetchone()
    return int(fila["posicion"])


# --- Esquema: los hitos de plan -------------------------------------------


def insertar_hito(base: Conexion, plan_hash: str, motivo: str, posicion: int) -> Esquema:
    with transaccion(base):
        cursor = base.execute(
            "INSERT INTO esquema (plan_hash, motivo, posicion, fijado_en) VALUES (?, ?, ?, ?)",
            (plan_hash, motivo, posicion, ahora()),
        )
    identificador = cursor.lastrowid
    assert identificador is not None
    return obtener_hito(base, identificador)


def obtener_hito(base: Conexion, hito_id: int) -> Esquema:
    fila = base.execute("SELECT * FROM esquema WHERE id = ?", (hito_id,)).fetchone()
    if fila is None:
        raise RecursoNoEncontrado(f"no existe el hito de plan {hito_id}")
    return Esquema.model_validate(dict(fila))


def ultimo_hito(base: Conexion) -> Esquema | None:
    fila = base.execute("SELECT * FROM esquema ORDER BY id DESC LIMIT 1").fetchone()
    return None if fila is None else Esquema.model_validate(dict(fila))


def hitos(base: Conexion) -> list[Esquema]:
    return [
        Esquema.model_validate(dict(fila))
        for fila in base.execute("SELECT * FROM esquema ORDER BY id")
    ]


# --- Brief y restricciones ------------------------------------------------


def insertar_brief(base: Conexion, datos: schemas.NuevoBrief) -> BriefDeEscena:
    """El brief y sus restricciones entran juntos o no entran.

    Un brief a medio escribir es un encargo sin destino, y un encargo sin destino
    es exactamente lo que el modo hibrido no permite.
    """
    with transaccion(base):
        cursor = base.execute(
            "INSERT INTO brief_escena (escena_id, estado_de_entrada, encargo, creado_en) "
            "VALUES (?, ?, ?, ?)",
            (datos.escena_id, datos.estado_de_entrada, datos.encargo, ahora()),
        )
        brief_id = cursor.lastrowid
        assert brief_id is not None
        for restriccion in datos.restricciones:
            base.execute(
                "INSERT INTO restriccion_destino (brief_id, tipo, enunciado, alcance, "
                "personaje_id, lugar_id, hecho_id, valor) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    brief_id,
                    restriccion.tipo.value,
                    restriccion.enunciado,
                    restriccion.alcance,
                    restriccion.personaje_id,
                    restriccion.lugar_id,
                    restriccion.hecho_id,
                    restriccion.valor,
                ),
            )
    return obtener_brief(base, brief_id)


def obtener_brief(base: Conexion, brief_id: int) -> BriefDeEscena:
    fila = base.execute("SELECT * FROM brief_escena WHERE id = ?", (brief_id,)).fetchone()
    if fila is None:
        raise RecursoNoEncontrado(f"no existe el brief {brief_id}")
    return BriefDeEscena.model_validate(dict(fila))


def brief_de_escena(base: Conexion, escena_id: int) -> BriefDeEscena | None:
    fila = base.execute("SELECT * FROM brief_escena WHERE escena_id = ?", (escena_id,)).fetchone()
    return None if fila is None else BriefDeEscena.model_validate(dict(fila))


def restricciones_de(base: Conexion, brief_id: int) -> list[RestriccionDeDestino]:
    return [
        RestriccionDeDestino.model_validate(dict(fila))
        for fila in base.execute(
            "SELECT * FROM restriccion_destino WHERE brief_id = ? ORDER BY id", (brief_id,)
        )
    ]


def restricciones_de_escenas_planificadas(base: Conexion) -> list[RestriccionDeDestino]:
    """Lo unico que el esquema declara del futuro.

    El orden es por `id` y no por discurso a proposito: la medida cuenta, no
    recorre, y un orden estable es lo que hace reproducible el `plan_hash`.
    """
    return [
        RestriccionDeDestino.model_validate(dict(fila))
        for fila in base.execute(
            """
            SELECT restriccion.*
            FROM restriccion_destino AS restriccion
            JOIN brief_escena AS brief ON brief.id = restriccion.brief_id
            JOIN escena ON escena.id = brief.escena_id
            WHERE escena.estado = ?
            ORDER BY restriccion.id
            """,
            (POR_ESCRIBIR,),
        )
    ]


def restricciones_posteriores_a(base: Conexion, escena_id: int) -> list[RestriccionDeDestino]:
    """Las de los briefs que vienen despues en el discurso (P-41, RF-PROC-11)."""
    return [
        RestriccionDeDestino.model_validate(dict(fila))
        for fila in base.execute(
            """
            SELECT restriccion.*
            FROM restriccion_destino AS restriccion
            JOIN brief_escena AS brief ON brief.id = restriccion.brief_id
            JOIN escena_ordenada AS orden ON orden.escena_id = brief.escena_id
            WHERE orden.posicion > (
                SELECT posicion FROM escena_ordenada WHERE escena_id = ?
            )
            ORDER BY restriccion.id
            """,
            (escena_id,),
        )
    ]


# --- Registro de generacion, borrador y version ---------------------------


def insertar_registro(base: Conexion, datos: schemas.NuevoRegistro) -> RegistroDeGeneracion:
    with transaccion(base):
        cursor = base.execute(
            "INSERT INTO registro_generacion (escena_id, agente, modelo, prompt, contexto, "
            "semilla, huella_prompt, huella_contexto, huella_parametros, tokens_de_entrada, "
            "tokens_de_salida, timeout_segundos, registrado_en) "
            "VALUES (:escena_id, :agente, :modelo, :prompt, :contexto, :semilla, "
            ":huella_prompt, :huella_contexto, :huella_parametros, :tokens_de_entrada, "
            ":tokens_de_salida, :timeout_segundos, :registrado_en)",
            {**datos.model_dump(), "registrado_en": ahora()},
        )
    identificador = cursor.lastrowid
    assert identificador is not None
    return obtener_registro(base, identificador)


def obtener_registro(base: Conexion, registro_id: int) -> RegistroDeGeneracion:
    fila = base.execute("SELECT * FROM registro_generacion WHERE id = ?", (registro_id,)).fetchone()
    if fila is None:
        raise RecursoNoEncontrado(f"no existe el registro de generacion {registro_id}")
    return RegistroDeGeneracion.model_validate(dict(fila))


def registros_de(base: Conexion, escena_id: int) -> list[RegistroDeGeneracion]:
    return [
        RegistroDeGeneracion.model_validate(dict(fila))
        for fila in base.execute(
            "SELECT * FROM registro_generacion WHERE escena_id = ? ORDER BY id", (escena_id,)
        )
    ]


def insertar_borrador(
    base: Conexion, brief_id: int, escena_id: int, texto: str, registro_id: int
) -> Borrador:
    with transaccion(base):
        intento = _siguiente(
            base,
            "SELECT COALESCE(MAX(intento), 0) + 1 AS n FROM borrador WHERE escena_id = ?",
            escena_id,
        )
        cursor = base.execute(
            "INSERT INTO borrador (brief_id, escena_id, intento, texto, registro_id, creado_en) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (brief_id, escena_id, intento, texto, registro_id, ahora()),
        )
    identificador = cursor.lastrowid
    assert identificador is not None
    return obtener_borrador(base, identificador)


def obtener_borrador(base: Conexion, borrador_id: int) -> Borrador:
    fila = base.execute("SELECT * FROM borrador WHERE id = ?", (borrador_id,)).fetchone()
    if fila is None:
        raise RecursoNoEncontrado(f"no existe el borrador {borrador_id}")
    return Borrador.model_validate(dict(fila))


def insertar_version(
    base: Conexion, escena_id: int, texto: str, origen: OrigenDeVersion, borrador_id: int | None
) -> Version:
    with transaccion(base):
        numero = _siguiente(
            base,
            "SELECT COALESCE(MAX(numero), 0) + 1 AS n FROM version WHERE escena_id = ?",
            escena_id,
        )
        cursor = base.execute(
            "INSERT INTO version (escena_id, numero, borrador_id, texto, origen, creada_en) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (escena_id, numero, borrador_id, texto, origen.value, ahora()),
        )
    identificador = cursor.lastrowid
    assert identificador is not None
    return obtener_version(base, identificador)


def obtener_version(base: Conexion, version_id: int) -> Version:
    fila = base.execute("SELECT * FROM version WHERE id = ?", (version_id,)).fetchone()
    if fila is None:
        raise RecursoNoEncontrado(f"no existe la version {version_id}")
    return Version.model_validate(dict(fila))


def versiones_de(base: Conexion, escena_id: int) -> list[Version]:
    return [
        Version.model_validate(dict(fila))
        for fila in base.execute(
            "SELECT * FROM version WHERE escena_id = ? ORDER BY numero", (escena_id,)
        )
    ]


def version_numero(base: Conexion, escena_id: int, numero: int) -> Version | None:
    fila = base.execute(
        "SELECT * FROM version WHERE escena_id = ? AND numero = ?", (escena_id, numero)
    ).fetchone()
    return None if fila is None else Version.model_validate(dict(fila))


def _siguiente(base: Conexion, consulta: str, escena_id: int) -> int:
    fila = base.execute(consulta, (escena_id,)).fetchone()
    return int(fila["n"])


# --- Banco de ejemplos ----------------------------------------------------


def insertar_muestra(base: Conexion, datos: schemas.NuevaMuestra) -> int:
    """Append-only y sin lectura en v1: aqui no hay `SELECT` que la devuelva."""
    with transaccion(base):
        cursor = base.execute(
            "INSERT INTO training_samples (escena_id, version_id, brief, contexto, "
            "texto_aceptado, editado_a_mano, modo_de_aceptacion, aceptado_en) "
            "VALUES (?, ?, ?, ?, ?, 1, 'humana', ?)",
            (
                datos.escena_id,
                datos.version_id,
                datos.brief,
                datos.contexto,
                datos.texto_aceptado,
                ahora(),
            ),
        )
    identificador = cursor.lastrowid
    assert identificador is not None
    return identificador


def contar_muestras(base: Conexion) -> int:
    """La unica lectura, y es un recuento: sirve para verificar la regla, no
    para alimentar a nadie."""
    fila = base.execute("SELECT COUNT(*) AS total FROM training_samples").fetchone()
    return int(fila["total"])


# --- Deriva ---------------------------------------------------------------


def guardar_medicion(
    base: Conexion,
    escena_id: int,
    hito: Esquema,
    medida: schemas.MedidaGuardable,
) -> Deriva:
    """La medicion y sus ingredientes, en una transaccion.

    Una medicion sin sus ingredientes no es una medicion a medias: es una cifra
    que ya no se puede recalcular, que es justo lo que RF-PROC-12 prohibe.
    """
    with transaccion(base):
        base.execute("DELETE FROM deriva_medicion WHERE escena_id = ?", (escena_id,))
        cursor = base.execute(
            "INSERT INTO deriva_medicion (escena_id, esquema_id, plan_hash, "
            "invalidacion_num, invalidacion_den, canon_huerfano_num, canon_huerfano_den, "
            "inviabilidad_num, inviabilidad_den, densidad_num, densidad_den, fiable, "
            "definicion_version, medido_en) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                escena_id,
                hito.id,
                hito.plan_hash,
                medida.invalidacion_num,
                medida.invalidacion_den,
                medida.canon_huerfano_num,
                medida.canon_huerfano_den,
                medida.inviabilidad_num,
                medida.inviabilidad_den,
                medida.densidad_num,
                medida.densidad_den,
                None if medida.fiable is None else int(medida.fiable),
                medida.definicion_version,
                ahora(),
            ),
        )
        medicion_id = cursor.lastrowid
        assert medicion_id is not None
        for ingrediente in medida.ingredientes:
            base.execute(
                "INSERT INTO deriva_ingrediente (medicion_id, componente, tipo_elemento, "
                "elemento_id, cuenta_en, motivo, hecho_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    medicion_id,
                    ingrediente.componente.value,
                    ingrediente.tipo_elemento.value,
                    ingrediente.elemento_id,
                    ingrediente.cuenta_en.value,
                    ingrediente.motivo.value,
                    ingrediente.hecho_id,
                ),
            )
    return obtener_medicion(base, escena_id)


def obtener_medicion(base: Conexion, escena_id: int) -> Deriva:
    fila = base.execute(
        "SELECT * FROM deriva_medicion WHERE escena_id = ?", (escena_id,)
    ).fetchone()
    if fila is None:
        raise RecursoNoEncontrado(f"la escena {escena_id} no tiene medicion de deriva")
    return _a_deriva(fila)


def mediciones(base: Conexion) -> list[Deriva]:
    return [
        _a_deriva(fila)
        for fila in base.execute(
            """
            SELECT medicion.* FROM deriva_medicion AS medicion
            JOIN escena_ordenada AS orden ON orden.escena_id = medicion.escena_id
            ORDER BY orden.posicion
            """
        )
    ]


def ingredientes_de(base: Conexion, escena_id: int) -> list[schemas.IngredienteGuardado]:
    return [
        schemas.IngredienteGuardado(
            componente=models.ComponenteDeDeriva(fila["componente"]),
            tipo_elemento=models.TipoDeElemento(fila["tipo_elemento"]),
            elemento_id=int(fila["elemento_id"]),
            cuenta_en=models.CuentaEn(fila["cuenta_en"]),
            motivo=models.MotivoDeIngrediente(fila["motivo"]),
            hecho_id=fila["hecho_id"],
        )
        for fila in base.execute(
            """
            SELECT ingrediente.* FROM deriva_ingrediente AS ingrediente
            JOIN deriva_medicion AS medicion ON medicion.id = ingrediente.medicion_id
            WHERE medicion.escena_id = ?
            ORDER BY ingrediente.id
            """,
            (escena_id,),
        )
    ]


def _a_deriva(fila: object) -> Deriva:
    datos = dict(fila)  # type: ignore[call-overload]
    datos["fiable"] = None if datos["fiable"] is None else bool(datos["fiable"])
    return Deriva.model_validate(datos)
