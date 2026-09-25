"""Chequeo incremental de Lean tras aceptar cada capítulo (RF-LEAN-04, P-81, TO-016).

Es un aviso: emite los cuatro scores con la etapa, deja una entrada en el audit log y no
cambia el estado de nada. Con el gate apagado, la novela se publica aunque avise.
"""

from __future__ import annotations

from functools import partial

import pytest

from app.versioning.lean import ejecutar as modulo_ejecutar
from tests.conftest import Entorno
from tests.dobles.guiones import guion_completo
from tests.versioning.test_gate_lean import LEAN, _en_dos_sitios, _generar, con_formal


@pytest.mark.anyio
async def test_una_violacion_avisa_y_no_detiene(entorno: Entorno) -> None:
    con_formal(entorno, gate_activo=False, lean_incremental=True)
    guion_completo(entorno.modelo)
    entorno.modelo.encolar("extractor", *[partial(_en_dos_sitios, n=n) for n in range(1, 11)])
    novela, g = await _generar(entorno)

    assert g.estado == "Publicada", g
    ubicacion = entorno.trazas.scores_de("lean_ubicacion")
    assert [s.valor for s in ubicacion] == [0.0] * 10
    assert [s.metadata for s in ubicacion] == [
        {"etapa": "incremental", "capitulo": n} for n in range(1, 11)
    ]
    for nombre in LEAN - {"lean_ubicacion"}:
        assert [s.valor for s in entorno.trazas.scores_de(nombre)] == [1.0] * 10, nombre
    avisos = entorno.consultar(
        "SELECT resultado, entrada FROM audit_log"
        " WHERE novel_id = ? AND regla = 'lean-incremental'",
        novela,
    )
    assert [a["resultado"] for a in avisos] == ["aviso"] * 10
    assert "lean_ubicacion" in avisos[0]["entrada"]
    estados = entorno.consultar("SELECT DISTINCT estado FROM capitulo WHERE novel_id = ?", novela)
    assert [e["estado"] for e in estados] == ["Aceptado"]


@pytest.mark.anyio
async def test_una_cronologia_limpia_queda_demostrada(entorno: Entorno) -> None:
    con_formal(entorno, gate_activo=False, lean_incremental=True)
    guion_completo(entorno.modelo)
    novela, g = await _generar(entorno)

    assert g.estado == "Publicada", g
    avisos = entorno.consultar(
        "SELECT resultado FROM audit_log WHERE novel_id = ? AND regla = 'lean-incremental'",
        novela,
    )
    assert [a["resultado"] for a in avisos] == ["demostrado"] * 10


@pytest.mark.anyio
async def test_sin_toolchain_avisa_sin_excepcion(
    entorno: Entorno, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(modulo_ejecutar, "buscar_lake", lambda: None)
    con_formal(entorno, gate_activo=False, lean_incremental=True)
    guion_completo(entorno.modelo)
    novela, g = await _generar(entorno)

    assert g.estado == "Publicada", g
    avisos = entorno.consultar(
        "SELECT resultado, entrada FROM audit_log"
        " WHERE novel_id = ? AND regla = 'lean-incremental'",
        novela,
    )
    assert len(avisos) == 10 and all(a["resultado"] == "aviso" for a in avisos)
    assert "toolchain-ausente" in avisos[0]["entrada"]


@pytest.mark.anyio
async def test_apagado_no_corre(entorno: Entorno) -> None:
    con_formal(entorno, gate_activo=False, lean_incremental=False)
    guion_completo(entorno.modelo)
    await _generar(entorno)
    assert not any(entorno.trazas.scores_de(n) for n in LEAN)
