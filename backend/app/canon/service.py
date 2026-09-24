"""Servicio de la story bible: lo único de `canon/` que otra feature puede importar.

**Solo aquí se escribe el canon, y solo al consolidar un capítulo aceptado** (RF-CANON-01).
`consolidar()` no abre la transacción: la abre quien acepta el capítulo (`process/`, D-07),
para que hechos, usos, promesas, snapshot, resumen, texto y checkpoint entren o no entren
juntos.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from uuid import UUID

from app.canon import repository
from app.canon.models import (
    Consolidacion,
    EstadoHecho,
    Hecho,
    HechoNuevo,
    HechoPropuesto,
    Promesa,
    PromesaNueva,
    ResultadoConsolidacion,
    Snapshot,
)
from app.canon.retcon import aplicar_retcon
from app.canon.schemas import HechoVigente
from app.commons.db import BaseDatos
from app.commons.errores import NovelaNoEncontrada, VersionNoEncontrada
from app.commons.tiempo import ahora

__all__ = [
    "Consolidacion",
    "EstadoHecho",
    "Hecho",
    "HechoNuevo",
    "HechoPropuesto",
    "HechoVigente",
    "Promesa",
    "PromesaNueva",
    "ResultadoConsolidacion",
    "Snapshot",
    "aplicar_retcon",
    "capitulos_que_usan",
    "consolidar",
    "fragmento_literal",
    "hechos_vigentes",
    "listar_hechos",
    "promesas_de",
    "promesas_pendientes_al_cierre",
    "retcon_de",
    "retirar_capitulo",
    "snapshot_de",
]


def fragmento_literal(fragmento: str, texto: str) -> bool:
    """El fragmento aparece tal cual en el texto. Es lo que ancla un hecho (RF-CANON-04)."""
    return bool(fragmento.strip()) and fragmento.strip() in texto


def consolidar(
    con: sqlite3.Connection,
    *,
    novel_id: str,
    version: int,
    texto: str,
    entrada: Consolidacion,
    decidir: Callable[[HechoPropuesto], bool],
) -> ResultadoConsolidacion:
    """Escribe en la story bible lo que un capítulo aceptado estableció y usó.

    Cada hecho nuevo entra como `propuesto` y `decidir` —el policy engine— lo adopta o lo
    descarta. Un hecho cuyo fragmento no está literal en el texto no llega a proponerse.
    Es idempotente por capítulo y versión: si el capítulo ya se consolidó, no escribe nada.
    """
    if repository.ya_consolidado(
        con, novel_id=novel_id, version=version, capitulo_id=entrada.capitulo_id
    ):
        return ResultadoConsolidacion(ya_consolidado=True)

    momento = ahora()
    resultado = ResultadoConsolidacion()
    for nuevo in entrada.hechos_nuevos:
        if not fragmento_literal(nuevo.fragmento_soporte, texto):
            resultado.sin_fragmento.append(nuevo)
            continue
        hecho_id = repository.insertar_hecho_propuesto(
            con,
            novel_id=novel_id,
            version=version,
            capitulo_id=entrada.capitulo_id,
            hecho=nuevo,
            ahora=momento,
        )
        propuesto = HechoPropuesto(
            hecho_id=hecho_id,
            enunciado=nuevo.enunciado,
            tipo=nuevo.tipo,
            fragmento_soporte=nuevo.fragmento_soporte,
        )
        if decidir(propuesto):
            repository.adoptar_hecho(con, novel_id=novel_id, version=version, hecho_id=hecho_id)
            repository.insertar_uso(
                con,
                novel_id=novel_id,
                version=version,
                hecho_id=hecho_id,
                capitulo_id=entrada.capitulo_id,
            )
            resultado.adoptados.append(propuesto)
        else:
            repository.descartar_hecho(con, novel_id=novel_id, version=version, hecho_id=hecho_id)
            resultado.descartados.append(propuesto)

    for hecho_id in entrada.hechos_usados:
        # Un uso solo se registra sobre un hecho vigente en esta versión: si el extractor cita
        # uno que no lo es, se ignora en vez de romper RD-05.
        if repository.hecho_es_vigente(con, novel_id=novel_id, version=version, hecho_id=hecho_id):
            repository.insertar_uso(
                con,
                novel_id=novel_id,
                version=version,
                hecho_id=hecho_id,
                capitulo_id=entrada.capitulo_id,
            )

    for promesa in entrada.promesas_abiertas:
        repository.insertar_promesa(
            con, novel_id=novel_id, capitulo_id=entrada.capitulo_id, promesa=promesa
        )
    for promesa_id in entrada.promesas_pagadas:
        repository.pagar_promesa(
            con, novel_id=novel_id, capitulo_id=entrada.capitulo_id, promesa_id=promesa_id
        )

    snapshot = Snapshot(
        numero=entrada.numero,
        momento=entrada.momento,
        personajes_presentes=entrada.personajes_presentes,
        ubicaciones=entrada.ubicaciones,
        hechos=[
            h.enunciado
            for h in repository.leer_hechos_vigentes(
                con, novel_id=novel_id, version=version, hasta_numero=entrada.numero
            )
        ],
        promesas_pendientes=repository.promesas_pendientes_hasta(
            con, novel_id=novel_id, version=version, numero=entrada.numero
        ),
    )
    repository.insertar_snapshot(
        con, novel_id=novel_id, capitulo_id=entrada.capitulo_id, snapshot=snapshot, ahora=momento
    )
    return resultado


def hechos_vigentes(
    con: sqlite3.Connection, *, novel_id: str, version: int, hasta_numero: int | None = None
) -> list[Hecho]:
    """Hechos vigentes en una versión, por vigencia y nunca por estatus (RF-CANON-03)."""
    return repository.leer_hechos_vigentes(
        con, novel_id=novel_id, version=version, hasta_numero=hasta_numero
    )


def capitulos_que_usan(
    con: sqlite3.Connection, *, novel_id: str, version: int, hecho_id: str
) -> list[int]:
    """Números de los capítulos que usan un hecho en una versión (pregunta 11)."""
    return repository.leer_capitulos_que_usan(
        con, novel_id=novel_id, version=version, hecho_id=hecho_id
    )


def snapshot_de(
    con: sqlite3.Connection, *, novel_id: str, version: int, capitulo_id: str
) -> Snapshot | None:
    """El snapshot al cierre de un capítulo **visto desde `version`** (D-12).

    Presentes y ubicaciones son los que se guardaron al aceptar el capítulo; los hechos se
    derivan de nuevo por vigencia en la versión pedida. Un capítulo no afectado por una
    regeneración conserva su fila, pero en la versión nueva su snapshot ya no dice el hecho
    retconeado sino el que lo sustituye (P43).
    """
    guardado = repository.leer_snapshot(
        con, novel_id=novel_id, version=version, capitulo_id=capitulo_id
    )
    if guardado is None:
        return None
    hechos = [
        h.enunciado
        for h in hechos_vigentes(
            con, novel_id=novel_id, version=version, hasta_numero=guardado.numero
        )
        if h.estado != "propuesto"
    ]
    return guardado.model_copy(update={"hechos": hechos})


def retirar_capitulo(
    con: sqlite3.Connection, *, novel_id: str, capitulo_id: str, version: int
) -> None:
    """Antes de reescribir un capítulo en `version`, lo que su fila vieja usaba deja de estar
    en uso desde `version`, y lo que establecía se cierra si nadie más lo usa. Lo que siga
    usando un capítulo no afectado se queda abierto: su texto no cambia (A-102)."""
    repository.retirar_capitulo(con, novel_id=novel_id, capitulo_id=capitulo_id, version=version)


def retcon_de(
    con: sqlite3.Connection, *, novel_id: str, solicitud_id: str
) -> tuple[str, str] | None:
    """`(enunciado viejo, enunciado nuevo)` del retcon que aplicó una solicitud."""
    return repository.leer_retcon(con, novel_id=novel_id, solicitud_id=solicitud_id)


def promesas_de(
    con: sqlite3.Connection, *, novel_id: str, version: int, capitulo_ids: list[str]
) -> list[Promesa]:
    return repository.leer_promesas(
        con, novel_id=novel_id, version=version, capitulo_ids=capitulo_ids
    )


def promesas_pendientes_al_cierre(
    con: sqlite3.Connection, *, novel_id: str, version: int, capitulo_ids: list[str]
) -> list[Promesa]:
    """Pregunta 18: promesas que siguen pendientes al llegar al último capítulo."""
    return [
        p
        for p in promesas_de(con, novel_id=novel_id, version=version, capitulo_ids=capitulo_ids)
        if p.estado == "pendiente"
    ]


async def listar_hechos(
    db: BaseDatos, novel_id: str, version: int, *, capitulo: int | None = None
) -> list[HechoVigente]:
    """Los hechos vigentes en una versión publicada, por vigencia (RF-CANON-03, TO-028); con
    `capitulo`, solo los que ese capítulo usa."""

    def leer(con: sqlite3.Connection) -> list[HechoVigente]:
        if not repository.existe_novela(con, novel_id=novel_id):
            raise NovelaNoEncontrada(novel_id=novel_id)
        if not repository.existe_version(con, novel_id=novel_id, version=version):
            raise VersionNoEncontrada(f"la novela no tiene versión {version}", novel_id=novel_id)
        return [
            HechoVigente(
                hecho_id=UUID(h.hecho_id),
                enunciado=h.enunciado,
                estado=h.estado,
                origen=h.origen,
                capitulo_establece=h.capitulo_establece,
                capitulos_usan=h.capitulos_usan,
                fragmento_soporte=h.fragmento_soporte,
            )
            for h in hechos_vigentes(con, novel_id=novel_id, version=version)
            if capitulo is None or capitulo in h.capitulos_usan
        ]

    return await db.ejecutar(leer)
