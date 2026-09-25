"""Humo real (L10 del plan 4, TO-067): el brief B2 de incoherencia temporal, de principio a fin.

Genera una novela con **exactamente** el brief que usará la evaluación
(`ejemplos/evaluacion/brief-b2-incoherencia-temporal.json`) contra un backend real en marcha
—con el gate activo, el servidor Playwright MCP y la página `lectura`— sobre una base propia, y
deja el resultado en `ejemplos/evaluacion/resultado-b2.json` para que la evaluación lo
reutilice sin regenerar mientras el código no cambie: commit, traza, scores de capítulo,
veredictos del gate, versiones, coste y desenlace.

Los veredictos del gate que no fallan no quedan en la base (solo en Langfuse, cuya API de
lectura devuelve 410 en esta organización), así que al terminar se recalculan sobre la
candidata con los mismos validadores: los que leen la base y Lean son deterministas.

    STORYMAKER_B2_URL=http://127.0.0.1:8000 STORYMAKER_B2_DB=data/storymaker-b2.db \\
        uv run --env-file ../.env pytest -m real tests/humo/test_lean_b2_real.py -v -s
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.commons.config import cargar_config
from app.commons.db import BaseDatos
from app.versioning.lean.ejecutar import verificar
from app.versioning.lean.generar import leer_cronologia
from app.versioning.service import Publicacion
from tests.arquitectura.comprobadores import RAIZ_REPO

pytestmark = pytest.mark.real

BRIEF = RAIZ_REPO / "ejemplos" / "evaluacion" / "brief-b2-incoherencia-temporal.json"
RESULTADO = RAIZ_REPO / "ejemplos" / "evaluacion" / "resultado-b2.json"
ESPERA_MAXIMA_S = 3 * 3600


def _commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=RAIZ_REPO, capture_output=True, text=True, check=True
    ).stdout.strip()


def _filas(con: sqlite3.Connection, sql: str, *p: Any) -> list[dict[str, Any]]:
    con.row_factory = sqlite3.Row
    return [dict(f) for f in con.execute(sql, p).fetchall()]


@pytest.mark.anyio
async def test_brief_b2_de_principio_a_fin() -> None:
    url = os.environ.get("STORYMAKER_B2_URL")
    ruta_db = os.environ.get("STORYMAKER_B2_DB")
    if not url or not ruta_db:
        pytest.skip("sin STORYMAKER_B2_URL y STORYMAKER_B2_DB: hace falta un backend en marcha")
    db_path = Path(ruta_db) if Path(ruta_db).is_absolute() else RAIZ_REPO / ruta_db
    config = cargar_config()
    assert config.umbrales.formal.gate_activo, "L10 corre con el gate de Lean activo"
    brief = json.loads(BRIEF.read_text(encoding="utf-8"))
    commit = _commit()
    inicio = time.monotonic()

    with httpx.Client(base_url=url, timeout=60) as http:
        salud = http.get("/salud").json()
        assert salud["gate_lean_activo"] is True, salud
        novela = http.post("/novelas", json=brief)
        assert novela.status_code == 201, novela.text
        novel_id = novela.json()["novel_id"]
        g = http.post(f"/novelas/{novel_id}/generaciones")
        assert g.status_code in (200, 201, 202), g.text
        gid = g.json()["generacion_id"]
        while True:
            estado = http.get(f"/novelas/{novel_id}/generaciones/{gid}").json()
            if estado["es_terminal"]:
                break
            assert time.monotonic() - inicio < ESPERA_MAXIMA_S, estado
            time.sleep(20)

    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        trabajo = _filas(
            con,
            "SELECT estado, detenida_por, version_objetivo, coste_usd, tokens_consumidos,"
            " traza_langfuse_id FROM trabajo WHERE id = ?",
            gid,
        )[0]
        versiones = _filas(
            con, "SELECT version, estado, hash FROM version_novela WHERE novel_id = ?", novel_id
        )
        scores_capitulo = _filas(
            con,
            "SELECT c.numero, i.intento, i.decision, s.validador, s.valor, s.pasa, s.detalle"
            " FROM score s JOIN informe_critica i ON i.id = s.informe_id"
            " JOIN capitulo c ON c.id = i.capitulo_id WHERE s.novel_id = ?"
            " ORDER BY c.numero, i.intento, s.orden",
            novel_id,
        )
        auditoria = _filas(
            con,
            "SELECT momento, sujeto, regla, resultado, entrada FROM audit_log"
            " WHERE novel_id = ? AND (regla IN ('lean-incremental', 'excluyente-sin-evento')"
            " OR resultado = 'detener') ORDER BY rowid",
            novel_id,
        )
        eventos = _filas(
            con,
            "SELECT e.momento, e.anio, e.descripcion, p.nombre, ep.edad FROM evento e"
            " JOIN evento_personaje ep ON ep.evento_id = e.id"
            " JOIN personaje p ON p.id = ep.personaje_id"
            " WHERE e.novel_id = ? AND e.anio IS NOT NULL ORDER BY e.momento",
            novel_id,
        )
    finally:
        con.close()

    version = trabajo["version_objetivo"]
    recalculado: list[dict[str, Any]] = []
    if any(v["version"] == version for v in versiones):
        db = BaseDatos(db_path)
        publicacion = Publicacion(config)
        gate = await db.ejecutar(lambda c: publicacion.gate(c, novel_id=novel_id, version=version))
        cronologia = await db.ejecutar(
            lambda c: leer_cronologia(c, novel_id=novel_id, version=version)
        )
        timeout = config.umbrales.formal.lean_timeout_segundos
        assert timeout is not None
        lean = await verificar(cronologia, timeout=timeout)
        recalculado = [
            {"nombre": v.nombre, "pasa": v.pasa, "valor": v.valor, "detalle": v.detalle}
            for v in [*gate, *lean.veredictos]
        ]

    resultado = {
        "brief": str(BRIEF.relative_to(RAIZ_REPO)).replace("\\", "/"),
        "commit": commit,
        "fecha": datetime.now(UTC).isoformat(timespec="seconds"),
        "novel_id": novel_id,
        "generacion_id": gid,
        "traza_langfuse": trabajo["traza_langfuse_id"],
        "estado": trabajo["estado"],
        "detenida_por": trabajo["detenida_por"],
        "version": version,
        "versiones": versiones,
        "coste_usd": trabajo["coste_usd"],
        "tokens": trabajo["tokens_consumidos"],
        "duracion_s": round(time.monotonic() - inicio),
        "gate_recalculado": recalculado,
        "auditoria": auditoria,
        "eventos_con_anio": eventos,
        "scores_capitulo": scores_capitulo,
        "desenlace": None,
    }
    RESULTADO.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {k: v for k, v in resultado.items() if k != "scores_capitulo"},
            ensure_ascii=False,
            indent=2,
        )[:6000]
    )
    assert trabajo["estado"] in ("Publicada", "Detenida")
