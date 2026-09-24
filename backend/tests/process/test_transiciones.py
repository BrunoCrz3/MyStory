"""La máquina de estados como dato, comparada con los documentos (RF-PROC-07, TO-020)."""

from __future__ import annotations

import re

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.commons.errores import TransicionInvalida
from app.process.transiciones import TRANSICIONES, acciones_desde, aplicar
from tests.arquitectura.comprobadores import RAIZ_REPO
from tests.contrato.normalizar import cargar_contrato

DOMINIO = (RAIZ_REPO / "docs" / "domain-knowledge.md").read_text(encoding="utf-8")
ARQUITECTURA = (RAIZ_REPO / "docs" / "architecture.md").read_text(encoding="utf-8")


def _diagrama(etiqueta: str) -> set[tuple[str, str]]:
    seccion = DOMINIO.split("## Estados", 1)[1]
    bloque = seccion.split(f"**{etiqueta}:**", 1)[1].split("```mermaid", 1)[1].split("```", 1)[0]
    pares = set()
    for origen, destino in re.findall(r"^\s*(\[\*\]|\w+)\s*-->\s*(\[\*\]|\w+)", bloque, re.M):
        if "[*]" not in (origen, destino):
            pares.add((origen, destino))
    return pares


def _tabla_arquitectura() -> list[tuple[str, str, str | None, str, str]]:
    seccion = ARQUITECTURA.split("| Acción TLA+ | Máquina |", 1)[1].split("\n\n", 1)[0]
    filas = []
    for linea in seccion.splitlines()[2:]:
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        accion, maquina, origen, destino, funcion = celdas
        filas.append(
            (
                accion.strip("`"),
                maquina,
                None if origen == "—" else origen.strip("`"),
                destino.strip("`"),
                funcion.split("·")[0].strip().strip("`"),
            )
        )
    return filas


def test_pares_del_capitulo_son_los_del_diagrama() -> None:
    codigo = {(t.origen, t.destino) for t in TRANSICIONES if t.maquina == "Capitulo" and t.origen}
    assert codigo == _diagrama("Capítulo")


def test_pares_de_la_novela_son_los_del_diagrama() -> None:
    codigo = {(t.origen, t.destino) for t in TRANSICIONES if t.maquina == "Novela" and t.origen}
    assert codigo == _diagrama("Novela")


def test_acciones_y_funciones_son_las_de_architecture() -> None:
    codigo = sorted((t.accion, t.maquina, t.origen, t.destino, t.funcion) for t in TRANSICIONES)
    assert codigo == sorted(_tabla_arquitectura())


def test_los_estados_son_los_del_contrato() -> None:
    esquemas = cargar_contrato()["components"]["schemas"]
    for maquina, enum in (("Capitulo", "EstadoCapitulo"), ("Novela", "EstadoNovela")):
        estados = {t.destino for t in TRANSICIONES if t.maquina == maquina} | {
            t.origen for t in TRANSICIONES if t.maquina == maquina and t.origen
        }
        declarados = set(esquemas[enum]["enum"])
        if maquina == "Novela":
            declarados.discard("Configurando")
            estados.discard("Configurando")
        assert estados == declarados


def test_una_transicion_que_no_esta_se_rechaza() -> None:
    with pytest.raises(TransicionInvalida, match="Aceptar"):
        aplicar("Capitulo", "Pendiente", "Aceptar")
    with pytest.raises(TransicionInvalida):
        aplicar("Novela", "Detenida", "Planificar")


def test_una_transicion_valida_devuelve_su_destino() -> None:
    assert aplicar("Capitulo", "Validando", "Reescribir") == "Reescribiendo"
    assert aplicar("Novela", "Escribiendo", "CerrarEscritura") == "Validando"
    assert aplicar("Capitulo", "Escribiendo", "Validar") == "Validando"


@given(st.lists(st.integers(min_value=0, max_value=20), max_size=30))
def test_ninguna_secuencia_valida_sale_de_los_estados_declarados(elecciones: list[int]) -> None:
    declarados = set(cargar_contrato()["components"]["schemas"]["EstadoCapitulo"]["enum"])
    estado = "Pendiente"
    for eleccion in elecciones:
        posibles = sorted(acciones_desde("Capitulo", estado))
        if not posibles:
            assert estado == "Agotado"
            break
        estado = aplicar("Capitulo", estado, posibles[eleccion % len(posibles)])
        assert estado in declarados
