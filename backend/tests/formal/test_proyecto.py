"""El proyecto Lake de la cronología: compila en verde y cada predicado caza su violación
en la línea del teorema de ese evento (A-91, O-13, O-14, O-15, O-66)."""

from __future__ import annotations

import re

import pytest

from app.versioning.lean.toolchain import PROYECTO_LEAN
from tests.formal.conftest import Lake

_ERROR = re.compile(r"error: .*?Cronologia[\\/](\w+)\.lean:(\d+):\d+:")

CABECERA = "import Cronologia.Basico\nopen Cronologia\n\n"

# Cada variante: definiciones, el teorema que debe fallar y uno de control que debe pasar.
VARIANTES = {
    "ubicacion": (
        "def a : Evento := Evento.mk 1 101 none (some 1) [Presencia.mk 1 none]\n"
        "def b : Evento := Evento.mk 2 101 none (some 2) [Presencia.mk 1 none]\n"
        "def c : Evento := Evento.mk 3 102 none (some 2) [Presencia.mk 1 none]\n"
        "def evs : List Evento := [a, b, c]\n",
        "theorem falla : ubicacionOk evs a = true := by decide",
        "theorem pasa : ubicacionOk evs c = true := by decide",
    ),
    "cronologia": (
        "def muere : Evento := Evento.mk 1 101 (some 2000) none [Presencia.mk 1 none]\n"
        "def vuelve : Evento := Evento.mk 2 102 (some 2001) none [Presencia.mk 1 none]\n"
        "def recuerdo : Evento := Evento.mk 3 201 (some 1999) none [Presencia.mk 1 none]\n"
        "def evs : List Evento := [muere, vuelve, recuerdo]\n"
        "def xs : List Excluyente := [Excluyente.mk 1 1]\n",
        "theorem falla : cronologiaOk evs xs vuelve = true := by decide",
        "theorem pasa : cronologiaOk evs xs recuerdo = true := by decide",
    ),
    "edad": (
        "def ns : List Nacimiento := [Nacimiento.mk 1 1980]\n"
        "def mal : Evento := Evento.mk 1 101 (some 1990) none [Presencia.mk 1 (some 12)]\n"
        "def bien : Evento := Evento.mk 2 102 (some 1990) none [Presencia.mk 1 (some 10)]\n",
        "theorem falla : edadOk ns mal = true := by decide",
        "theorem pasa : edadOk ns bien = true := by decide",
    ),
    "nacimiento": (
        "def ns : List Nacimiento := [Nacimiento.mk 1 1980]\n"
        "def antes : Evento := Evento.mk 1 101 (some 1975) none [Presencia.mk 1 none]\n"
        "def mismo : Evento := Evento.mk 2 102 (some 1980) none [Presencia.mk 1 none]\n",
        "theorem falla : nacimientoOk ns antes = true := by decide",
        "theorem pasa : nacimientoOk ns mismo = true := by decide",
    ),
}


def _lineas_con_error(salida: str, modulo: str) -> set[int]:
    return {int(n) for m, n in _ERROR.findall(salida) if m == modulo}


def test_el_proyecto_versionado_compila(lake: Lake) -> None:
    # El fixture ya construyó la copia entera, `Ejemplo.lean` incluido.
    assert (lake.proyecto / ".lake").is_dir()


@pytest.mark.parametrize("invariante", sorted(VARIANTES))
def test_una_violacion_falla_en_la_linea_de_su_teorema(lake: Lake, invariante: str) -> None:
    definiciones, falla, pasa = VARIANTES[invariante]
    texto = CABECERA + definiciones + "\n" + falla + "\n" + pasa + "\n"
    modulo = f"Variante{invariante.capitalize()}"
    r = lake.construir(modulo, texto)
    salida = r.stdout + r.stderr
    assert r.returncode != 0, salida
    linea_falla = texto.splitlines().index(falla) + 1
    assert _lineas_con_error(salida, modulo) == {linea_falla}, salida


def test_sin_mathlib_ni_require() -> None:
    configuracion = (PROYECTO_LEAN / "lakefile.toml").read_text(encoding="utf-8")
    sin_comentarios = [ln for ln in configuracion.splitlines() if not ln.lstrip().startswith("#")]
    assert not any("require" in ln for ln in sin_comentarios)
    for f in PROYECTO_LEAN.rglob("*.lean"):
        if ".lake" in f.parts:
            continue
        texto = f.read_text(encoding="utf-8")
        assert "import Mathlib" not in texto and "import Batteries" not in texto, f
