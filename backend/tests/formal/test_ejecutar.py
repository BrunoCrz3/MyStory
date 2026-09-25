"""Ejecutor e informe: `lake build` real sobre story bibles sintéticas (RF-LEAN-02, O-13,
O-14, O-15, O-66, spec 4 § 5.3 a § 5.5 y § 5.7)."""

from __future__ import annotations

import pytest

from app.novel.service import EventoVigente, PresenciaEnEvento
from app.process.service import VeredictoGate
from app.versioning.lean import ejecutar as modulo_ejecutar
from app.versioning.lean.ejecutar import verificar
from app.versioning.lean.generar import Cronologia, ExcluyenteDeVersion, PersonajeDeVersion

TIMEOUT = 120.0
ANA, BRUNO = "p-ana", "p-bruno"
PUERTO, FARO = "l-puerto", "l-faro"


def _ev(
    eid: str,
    momento: int,
    anio: int | None = None,
    lugar: str | None = PUERTO,
    presentes: dict[str, int | None] | None = None,
) -> EventoVigente:
    return EventoVigente(
        evento_id=eid,
        capitulo_id=f"c{momento // 100}",
        numero=momento // 100,
        momento=momento,
        anio=anio,
        lugar_id=lugar,
        presentes=[
            PresenciaEnEvento(personaje_id=p, edad=e) for p, e in (presentes or {ANA: None}).items()
        ],
    )


def _cron(
    eventos: list[EventoVigente],
    excluyentes: list[tuple[str, str]] | None = None,
    nacimientos: dict[str, int] | None = None,
) -> Cronologia:
    nacimientos = nacimientos if nacimientos is not None else {ANA: 1980}
    return Cronologia(
        novel_id="n",
        version=1,
        eventos=eventos,
        excluyentes=[
            ExcluyenteDeVersion(evento_id=e, personaje_id=p, tipo="muerte")
            for e, p in (excluyentes or [])
        ],
        personajes=[
            PersonajeDeVersion(
                personaje_id=ANA, nombre="Ana", anio_nacimiento=nacimientos.get(ANA)
            ),
            PersonajeDeVersion(
                personaje_id=BRUNO, nombre="Bruno", anio_nacimiento=nacimientos.get(BRUNO)
            ),
        ],
    )


def _por_nombre(veredictos: list[VeredictoGate]) -> dict[str, VeredictoGate]:
    return {v.nombre: v for v in veredictos}


async def _verificar(c: Cronologia, timeout: float = TIMEOUT) -> dict[str, VeredictoGate]:
    resultado = await verificar(c, timeout=timeout)
    return _por_nombre(resultado.veredictos)


def _solo_falla(v: dict[str, VeredictoGate], nombre: str) -> None:
    assert set(v) == {"lean_cronologia", "lean_ubicacion", "lean_edad", "lean_nacimiento"}
    fallidos = {n for n, x in v.items() if not x.pasa}
    assert fallidos == {nombre}, {n: x.detalle for n, x in v.items()}
    assert v[nombre].valor == 0.0


@pytest.mark.anyio
async def test_ubicacion_dos_lugares_en_el_mismo_momento() -> None:
    v = await _verificar(_cron([_ev("a", 101), _ev("b", 101, lugar=FARO), _ev("c", 102)]))
    _solo_falla(v, "lean_ubicacion")
    assert "capítulo 1" in v["lean_ubicacion"].detalle and "Ana" in v["lean_ubicacion"].detalle


@pytest.mark.anyio
async def test_cronologia_aparece_despues_de_morir() -> None:
    eventos = [
        _ev("muere", 101, anio=2000, presentes={BRUNO: None}),
        _ev("vuelve", 301, anio=2003, presentes={BRUNO: None}),
    ]
    v = await _verificar(_cron(eventos, excluyentes=[("muere", BRUNO)]))
    _solo_falla(v, "lean_cronologia")
    assert "vuelve" in v["lean_cronologia"].detalle and "Bruno" in v["lean_cronologia"].detalle


@pytest.mark.anyio
async def test_edad_declarada_que_no_cuadra() -> None:
    v = await _verificar(_cron([_ev("fiesta", 201, anio=1990, presentes={ANA: 12})]))
    _solo_falla(v, "lean_edad")
    assert "capítulo 2" in v["lean_edad"].detalle


@pytest.mark.anyio
async def test_nacimiento_evento_anterior_a_nacer() -> None:
    v = await _verificar(_cron([_ev("conoce", 101, anio=1975)]))
    _solo_falla(v, "lean_nacimiento")
    assert "conoce" in v["lean_nacimiento"].detalle


@pytest.mark.anyio
async def test_una_analepsis_no_es_una_incoherencia() -> None:
    eventos = [
        _ev("hoy", 101, anio=2020, presentes={ANA: 40}),
        _ev("recuerdo", 201, anio=1990, presentes={ANA: 10}),
    ]
    v = await _verificar(_cron(eventos))
    assert all(x.pasa for x in v.values()), {n: x.detalle for n, x in v.items()}


@pytest.mark.anyio
async def test_datos_vacios_no_se_comprueban_y_se_cuentan() -> None:
    eventos = [
        _ev("sin_anio", 101, presentes={ANA: 7}),
        _ev("sin_lugar", 102, anio=1990, lugar=None, presentes={BRUNO: 3}),
    ]
    v = await _verificar(_cron(eventos))
    assert all(x.pasa for x in v.values()), {n: x.detalle for n, x in v.items()}
    assert "sin comprobar: 2 de 2" in v["lean_edad"].detalle
    assert "sin comprobar: 1 de 2" in v["lean_ubicacion"].detalle


@pytest.mark.anyio
async def test_mismo_anio_de_nacimiento_o_de_exclusion_no_es_violacion() -> None:
    eventos = [
        _ev("nace", 101, anio=1980, presentes={ANA: 0}),
        _ev("muere", 201, anio=1999, presentes={BRUNO: None}),
        _ev("entierro", 202, anio=1999, presentes={BRUNO: None}),
    ]
    v = await _verificar(_cron(eventos, excluyentes=[("muere", BRUNO)]))
    assert all(x.pasa for x in v.values()), {n: x.detalle for n, x in v.items()}


@pytest.mark.anyio
async def test_sin_eventos_es_verde_y_lo_dice() -> None:
    v = await _verificar(_cron([]))
    assert all(x.pasa for x in v.values())
    assert "0 eventos" in v["lean_cronologia"].detalle


@pytest.mark.anyio
async def test_timeout_es_rojo_nunca_excepcion() -> None:
    resultado = await verificar(_cron([_ev("a", 101)]), timeout=0.001)
    assert resultado.estado == "timeout"
    assert [v.pasa for v in resultado.veredictos] == [False] * 4
    assert all("timeout" in v.detalle for v in resultado.veredictos)


@pytest.mark.anyio
async def test_sin_toolchain_es_rojo_nunca_excepcion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(modulo_ejecutar, "buscar_lake", lambda: None)
    resultado = await verificar(_cron([_ev("a", 101)]), timeout=TIMEOUT)
    assert resultado.estado == "toolchain-ausente"
    assert [v.pasa for v in resultado.veredictos] == [False] * 4
    assert all("toolchain-ausente" in v.detalle for v in resultado.veredictos)
