"""Humo real (L09 del plan 4, TO-067): Lean sobre datos reales, en una copia de la base.

Copia `data/storymaker-demo.db`, la migra, vuelve a extraer con el extractor real los capítulos
de la versión publicada que se pida —por defecto, la 3 de la novela de la demo— **en la
copia**, reemplazando solo sus eventos, y pasa el generador y `lake build`. La base real no se
abre en escritura: la prueba compara su hash antes y después (regla 2).

Un rojo de Lean aquí **no** es un rojo de la prueba: es un hallazgo, y se documenta. El
resumen queda en `data/lean-copia-<fecha>.json`.

    uv run --env-file ../.env pytest -m real tests/humo/test_lean_copia_real.py -v -s
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.canon import service as canon
from app.commons.config import cargar_config
from app.commons.db import BaseDatos
from app.commons.db.migrar import aplicar_migraciones
from app.commons.llm import crear_cliente
from app.commons.llm.llamar import LlamadorModelo
from app.commons.llm.pool import PoolEnVuelo
from app.commons.observabilidad import TrazadorLangfuse
from app.commons.recursos import Recursos
from app.intake import service as intake
from app.novel import service as novel
from app.process.aceptar import _Conocido, _extraer
from app.versioning.lean.ejecutar import verificar
from app.versioning.lean.generar import leer_cronologia
from tests.arquitectura.comprobadores import RAIZ_REPO
from tests.humo.test_novela_real import motivo_para_saltar

pytestmark = pytest.mark.real

ORIGEN = RAIZ_REPO / "data" / "storymaker-demo.db"
NOVELA = os.environ.get("STORYMAKER_LEAN_NOVELA", "9a9970e0-b5c9-415f-8eec-c952cccd6335")
VERSION = int(os.environ.get("STORYMAKER_LEAN_VERSION", "3"))


def _hash(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def _capitulos(con: sqlite3.Connection) -> list[dict[str, Any]]:
    filas = con.execute(
        "SELECT c.id, c.numero, c.version, c.texto FROM version_capitulo vc"
        " JOIN capitulo c ON c.id = vc.capitulo_id"
        " WHERE vc.novel_id = ? AND vc.version = ? ORDER BY vc.numero",
        (NOVELA, VERSION),
    ).fetchall()
    return [dict(f) for f in filas]


def _borrar_eventos(con: sqlite3.Connection, capitulo_id: str) -> None:
    """Solo en la copia: los eventos viejos del capítulo, para escribir los re-extraídos."""
    ids = [
        r[0]
        for r in con.execute(
            "SELECT evento_id FROM evento_capitulo WHERE capitulo_id = ?", (capitulo_id,)
        )
    ]
    for tabla in ("evento_excluyente", "evento_personaje", "evento_capitulo"):
        con.executemany(f"DELETE FROM {tabla} WHERE evento_id = ?", [(i,) for i in ids])
    con.executemany("DELETE FROM evento WHERE id = ?", [(i,) for i in ids])


@pytest.mark.anyio
async def test_lean_sobre_la_version_publicada_reextraida_en_una_copia(tmp_path: Path) -> None:
    config = cargar_config()
    if motivo := motivo_para_saltar(config):
        pytest.skip(motivo)
    if not ORIGEN.is_file():
        pytest.skip(f"no existe {ORIGEN}")
    hash_antes = _hash(ORIGEN)
    copia = tmp_path / "copia.db"
    shutil.copy(ORIGEN, copia)
    db = BaseDatos(copia)
    db.ejecutar_sync(aplicar_migraciones)
    trazador = TrazadorLangfuse()
    pool = PoolEnVuelo(config.umbrales.en_vuelo.total)
    r = Recursos(
        config=config,
        db=db,
        pool=pool,
        trazador=trazador,
        llamador=LlamadorModelo(config, crear_cliente(config), pool, trazador),
    )
    capitulos = db.ejecutar_sync(_capitulos)
    assert len(capitulos) == config.umbrales.obra.capitulos

    resumen: dict[str, Any] = {"novela": NOVELA, "version": VERSION, "capitulos": []}
    with trazador.traza("lean", novel_id=NOVELA, metadata={"etapa": "copia"}) as traza:
        resumen["traza"] = traza.traza_id
        for c in capitulos:

            def leer(con: sqlite3.Connection, c: dict[str, Any] = c) -> Any:
                filas = [x["id"] for x in capitulos if x["numero"] != c["numero"]]
                conocido = _Conocido(
                    canon.hechos_vigentes(con, novel_id=NOVELA, version=VERSION),
                    canon.promesas_vivas(
                        con,
                        novel_id=NOVELA,
                        numero=c["numero"],
                        filas_version=filas,
                        fila_anterior=None,
                    ),
                    filas=filas,
                    reescrito=False,
                )
                elementos = [e for _, e, _ in intake.elementos_personalizados(con, novel_id=NOVELA)]
                return conocido, elementos, novel.nombres_de_la_obra(con, novel_id=NOVELA)

            conocido, elementos, nombres = await db.ejecutar(leer)
            extraccion = await _extraer(
                r,
                capitulo_id=c["id"],
                texto=c["texto"],
                conocido=conocido,
                elementos=elementos,
                nombres=nombres,
                novel_id=NOVELA,
            )
            base = c["numero"] * 100

            def escribir(
                con: sqlite3.Connection,
                c: dict[str, Any] = c,
                ex: Any = extraccion,
                base: int = base,
            ) -> list[Any]:
                _borrar_eventos(con, c["id"])
                novel.registrar_eventos(
                    con,
                    novel_id=NOVELA,
                    version=c["version"],
                    capitulo_id=c["id"],
                    eventos=[
                        novel.EventoNarrado(
                            descripcion=e.descripcion,
                            momento=base + e.orden,
                            lugar=e.lugar,
                            personajes=e.personajes,
                            anio=e.anio,
                            edades={d.personaje: d.edad for d in e.edades},
                        )
                        for e in ex.eventos
                    ],
                )
                return novel.registrar_excluyentes(
                    con,
                    novel_id=NOVELA,
                    version=c["version"],
                    capitulo_id=c["id"],
                    excluyentes=[
                        novel.ExcluyenteNarrado(
                            personaje=x.personaje, tipo=x.tipo, momento=base + x.orden
                        )
                        for x in ex.excluyentes
                    ],
                )

            descartados = await db.en_transaccion(escribir)
            resumen["capitulos"].append(
                {
                    "numero": c["numero"],
                    "eventos": len(extraccion.eventos),
                    "con_anio": sum(e.anio is not None for e in extraccion.eventos),
                    "edades": sum(len(e.edades) for e in extraccion.eventos),
                    "excluyentes": len(extraccion.excluyentes),
                    "excluyentes_descartados": len(descartados),
                }
            )
        cronologia = await db.ejecutar(
            lambda con: leer_cronologia(con, novel_id=NOVELA, version=VERSION)
        )
        timeout = config.umbrales.formal.lean_timeout_segundos
        assert timeout is not None
        resultado = await verificar(cronologia, timeout=timeout)
        for v in resultado.veredictos:
            trazador.score(
                v.nombre, v.valor, comentario=v.detalle[:2000], metadata={"etapa": "copia"}
            )
    trazador.cerrar()

    resumen["lean"] = {
        "estado": resultado.estado,
        "duracion_segundos": resultado.duracion_segundos,
        "eventos": resultado.eventos,
        "veredictos": [
            {"nombre": v.nombre, "pasa": v.pasa, "detalle": v.detalle} for v in resultado.veredictos
        ],
    }
    fecha = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    salida = RAIZ_REPO / "data" / f"lean-copia-{fecha}.json"
    salida.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resumen, ensure_ascii=False, indent=2))

    assert _hash(ORIGEN) == hash_antes, "la base real cambió: la prueba solo puede tocar la copia"
    assert resultado.estado in ("demostrado", "fallos"), resultado
