"""El registro de validadores es el índice de `docs/verification.md`, leído del fichero (P28).

Plan § 4.3: el registro de `quality/` y el índice no pueden desincronizarse en silencio. Si
alguien cambia el tipo, el punto de ejecución o el score de un validador en uno de los dos
sitios, esta prueba falla.
"""

from __future__ import annotations

import re

import pytest

from app.commons.config import cargar_config
from app.quality.registro import REGISTRO, ValidadorNoRegistrado, comprobar, validador
from app.quality.validadores.basicos import longitud
from tests.arquitectura.comprobadores import RAIZ_REPO

VERIFICACION = RAIZ_REPO / "docs" / "verification.md"
CABECERA = "| Validador | Tipo | Punto de ejecución | Score en Langfuse | Filas que sostiene |"


def _limpio(celda: str) -> str:
    return re.sub(r"[*`]", "", celda).strip()


def indice() -> list[tuple[str, str, str, str, tuple[str, ...]]]:
    lineas = VERIFICACION.read_text(encoding="utf-8").splitlines()
    inicio = lineas.index(CABECERA) + 2
    filas = []
    for linea in lineas[inicio:]:
        if not linea.startswith("|"):
            break
        etiqueta, tipo, punto, score, sostiene = (_limpio(c) for c in linea.strip("|").split("|"))
        filas.append((score, etiqueta, tipo, punto, tuple(f.strip() for f in sostiene.split(","))))
    return filas


def test_el_indice_se_lee_entero() -> None:
    assert len(indice()) == 26


def test_el_registro_es_el_indice_de_verification() -> None:
    registro = [(v.nombre, v.etiqueta, v.tipo, v.punto, v.filas) for v in REGISTRO]
    assert registro == indice()


def test_los_nombres_de_score_son_unicos() -> None:
    nombres = [v.nombre for v in REGISTRO]
    assert len(nombres) == len(set(nombres))


def test_un_resultado_que_no_coincide_con_su_registro_falla_en_voz_alta() -> None:
    bueno = longitud(cargar_config(), "palabra " * 1200)
    comprobar(bueno)
    assert validador("longitud").punto == "hook de capítulo"

    with pytest.raises(ValidadorNoRegistrado, match="inventado"):
        comprobar(bueno.model_copy(update={"nombre": "inventado"}))
    with pytest.raises(ValidadorNoRegistrado, match="punto"):
        comprobar(bueno.model_copy(update={"punto": "gate de publicación"}))
