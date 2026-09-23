"""SQL explicito de `context/`, incluida la frontera con `vec0`.

El orden de consulta no es negociable: filtro relacional por las entidades del
brief y **despues**, y solo sobre ese conjunto, similitud vectorial. Nunca
similitud sola.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlite_vec import serialize_float32

from app.commons.db.conexion import Conexion, transaccion
from app.commons.errores import RecursoNoEncontrado
from app.context import models, schemas
from app.context.models import Fragmento, NivelDeCompresion, TipoDeUso, UsoDeRecurso


def insertar_fragmento(
    base: Conexion, datos: schemas.NuevoFragmento, modelo: str, version: str
) -> Fragmento:
    with transaccion(base):
        cursor = base.execute(
            "INSERT INTO fragmento (escena_id, texto, nivel, embedding_model, "
            "embedding_version, indexado_en) "
            "VALUES (:escena_id, :texto, :nivel, :modelo, :version, :indexado_en)",
            {
                "escena_id": datos.escena_id,
                "texto": datos.texto,
                "nivel": datos.nivel.value,
                "modelo": modelo,
                "version": version,
                "indexado_en": datetime.now(UTC).isoformat(),
            },
        )
        fragmento_id = cursor.lastrowid
        assert fragmento_id is not None

        base.execute(
            "INSERT INTO vec_fragmento (fragmento_id, embedding) VALUES (?, ?)",
            (fragmento_id, serialize_float32(datos.embedding)),
        )
        for entidad in datos.entidades:
            base.execute(
                "INSERT OR IGNORE INTO fragmento_entidad (fragmento_id, tipo, entidad_id) "
                "VALUES (?, ?, ?)",
                (fragmento_id, entidad.tipo, entidad.id),
            )
    return obtener_fragmento(base, fragmento_id)


def obtener_fragmento(base: Conexion, fragmento_id: int) -> Fragmento:
    fila = base.execute("SELECT * FROM fragmento WHERE id = ?", (fragmento_id,)).fetchone()
    if fila is None:
        raise RecursoNoEncontrado(f"no existe el fragmento {fragmento_id}")
    return Fragmento.model_validate(dict(fila))


def recuperar(
    base: Conexion,
    entidades: list[schemas.Referencia],
    consulta: list[float] | None,
    maximo: int,
) -> list[schemas.FragmentoRecuperado]:
    """Dos etapas, en este orden y no en el otro.

    1. Filtro relacional por las entidades declaradas en el brief.
    2. Similitud vectorial **solo sobre ese conjunto**.

    Sin entidades no hay primera etapa, y por tanto no hay recuperacion: la
    similitud a solas devuelve fragmentos de tono parecido y estado irrelevante.
    """
    if not entidades:
        return []

    condiciones = " OR ".join("(tipo = ? AND entidad_id = ?)" for _ in entidades)
    parametros: list[object] = []
    for entidad in entidades:
        parametros.extend((entidad.tipo, entidad.id))

    candidatos = [
        int(fila["fragmento_id"])
        for fila in base.execute(
            f"SELECT DISTINCT fragmento_id FROM fragmento_entidad WHERE {condiciones}",
            parametros,
        )
    ]
    if not candidatos:
        return []

    if consulta is None:
        distancias = dict.fromkeys(candidatos, 0.0)
    else:
        # `vec0` no admite `IN` sobre la clave en un KNN, asi que se pide el
        # vecindario y se cruza con el conjunto ya filtrado. El filtro sigue
        # yendo primero: lo que no esta en `candidatos` no puede salir.
        distancias = {}
        filas = base.execute(
            "SELECT fragmento_id, distance FROM vec_fragmento "
            "WHERE embedding MATCH ? AND k = ? ORDER BY distance",
            (serialize_float32(consulta), max(len(candidatos), maximo)),
        )
        for fila in filas:
            identificador = int(fila["fragmento_id"])
            if identificador in set(candidatos):
                distancias[identificador] = float(fila["distance"])

    if not distancias:
        return []

    marcadores = ", ".join("?" for _ in distancias)
    filas = base.execute(f"SELECT * FROM fragmento WHERE id IN ({marcadores})", list(distancias))
    fragmentos = {int(fila["id"]): dict(fila) for fila in filas}

    ordenados = sorted(distancias.items(), key=lambda par: (par[1], par[0]))
    return [
        schemas.FragmentoRecuperado(
            id=identificador,
            escena_id=fragmentos[identificador]["escena_id"],
            texto=fragmentos[identificador]["texto"],
            nivel=NivelDeCompresion(fragmentos[identificador]["nivel"]),
            distancia=distancia,
        )
        for identificador, distancia in ordenados[:maximo]
        if identificador in fragmentos
    ]


def fragmentos_de(base: Conexion, escena_id: int, nivel: NivelDeCompresion) -> list[Fragmento]:
    return [
        Fragmento.model_validate(dict(fila))
        for fila in base.execute(
            "SELECT * FROM fragmento WHERE escena_id = ? AND nivel = ? ORDER BY id",
            (escena_id, nivel.value),
        )
    ]


def niveles_de(base: Conexion, escena_id: int) -> list[NivelDeCompresion]:
    return [
        NivelDeCompresion(fila["nivel"])
        for fila in base.execute(
            "SELECT DISTINCT nivel FROM fragmento WHERE escena_id = ?", (escena_id,)
        )
    ]


def literales_hasta(base: Conexion, posicion: int, cuantas: int) -> list[Fragmento]:
    """Las ultimas escenas literales, de la mas reciente hacia atras."""
    return [
        Fragmento.model_validate(dict(fila))
        for fila in base.execute(
            """
            SELECT fragmento.*
            FROM fragmento
            JOIN escena_ordenada AS orden ON orden.escena_id = fragmento.escena_id
            WHERE fragmento.nivel = 'escena_literal' AND orden.posicion <= ?
            ORDER BY orden.posicion DESC, fragmento.id DESC
            LIMIT ?
            """,
            (posicion, cuantas),
        )
    ]


def muestras_de_voz(
    base: Conexion, personajes: list[int], posicion: int, cuantas: int
) -> list[Fragmento]:
    """`muestrear-voz`: fragmentos literales de los personajes presentes.

    De los presentes, no de todos: una muestra de quien no esta en la escena
    gasta la capa Estilo sin mejorar ninguna voz.
    """
    if not personajes:
        return []
    marcadores = ", ".join("?" for _ in personajes)
    return [
        Fragmento.model_validate(dict(fila))
        for fila in base.execute(
            f"""
            SELECT DISTINCT fragmento.*
            FROM fragmento
            JOIN fragmento_entidad AS puente ON puente.fragmento_id = fragmento.id
            JOIN escena_ordenada AS orden ON orden.escena_id = fragmento.escena_id
            WHERE puente.tipo = 'personaje' AND puente.entidad_id IN ({marcadores})
              AND fragmento.nivel = 'escena_literal' AND orden.posicion <= ?
            ORDER BY orden.posicion DESC, fragmento.id DESC
            LIMIT ?
            """,
            (*personajes, posicion, cuantas),
        )
    ]


def entidades_presentadas(base: Conexion, posicion: int) -> list[schemas.Referencia]:
    return [
        schemas.Referencia(tipo=str(fila["tipo"]), id=int(fila["entidad_id"]))
        for fila in base.execute(
            """
            SELECT DISTINCT puente.tipo AS tipo, puente.entidad_id AS entidad_id
            FROM fragmento_entidad AS puente
            JOIN fragmento ON fragmento.id = puente.fragmento_id
            JOIN escena_ordenada AS orden ON orden.escena_id = fragmento.escena_id
            WHERE orden.posicion <= ?
            ORDER BY puente.tipo, puente.entidad_id
            """,
            (posicion,),
        )
    ]


def insertar_uso(base: Conexion, datos: schemas.NuevoUso) -> UsoDeRecurso:
    with transaccion(base):
        cursor = base.execute(
            "INSERT INTO uso_de_recurso (escena_id, tipo, texto, registrado_en) "
            "VALUES (?, ?, ?, ?)",
            (
                datos.escena_id,
                datos.tipo.value,
                datos.texto,
                datetime.now(UTC).isoformat(),
            ),
        )
        identificador = cursor.lastrowid
    assert identificador is not None
    fila = base.execute("SELECT * FROM uso_de_recurso WHERE id = ?", (identificador,)).fetchone()
    return UsoDeRecurso.model_validate(dict(fila))


def usos_en_ventana(
    base: Conexion, posicion: int, ventana_escenas: int | None
) -> list[UsoDeRecurso]:
    """Ventana deslizante: cuanto se recuerda antes de olvidar.

    Sin ventana declarada no se olvida nada. Es la misma politica que el resto
    de umbrales en `null`: se mide y se informa, no se inventa un numero.
    """
    desde = 0 if ventana_escenas is None else posicion - ventana_escenas + 1
    return [
        UsoDeRecurso.model_validate(dict(fila))
        for fila in base.execute(
            """
            SELECT uso.*
            FROM uso_de_recurso AS uso
            JOIN escena_ordenada AS orden ON orden.escena_id = uso.escena_id
            WHERE orden.posicion <= ? AND orden.posicion >= ?
            ORDER BY orden.posicion, uso.id
            """,
            (posicion, desde),
        )
    ]


def modelos_indexados(base: Conexion) -> set[tuple[str, str]]:
    return {
        (str(fila["embedding_model"]), str(fila["embedding_version"]))
        for fila in base.execute(
            "SELECT DISTINCT embedding_model, embedding_version FROM fragmento"
        )
    }


def dimension_declarada_en_vec0(base: Conexion) -> int | None:
    """La dimension con la que se creo la tabla virtual, leida del esquema."""
    fila = base.execute("SELECT sql FROM sqlite_master WHERE name = 'vec_fragmento'").fetchone()
    if fila is None:
        return None
    import re

    encontrado = re.search(r"float\[(\d+)\]", str(fila["sql"]))
    return None if encontrado is None else int(encontrado.group(1))


__all__ = [
    "TipoDeUso",
    "dimension_declarada_en_vec0",
    "entidades_presentadas",
    "fragmentos_de",
    "insertar_fragmento",
    "insertar_uso",
    "literales_hasta",
    "models",
    "modelos_indexados",
    "muestras_de_voz",
    "niveles_de",
    "obtener_fragmento",
    "recuperar",
    "usos_en_ventana",
]
