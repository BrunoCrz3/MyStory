"""H3 · prueba 4 — A-17 y A-26, por analisis estatico.

Las dos afirman algo sobre todo el codigo, no sobre un camino: «toda escritura»
y «solo `canon/`». Una prueba de comportamiento diria que el camino que ejercita
cumple, y callaria sobre los demas.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CODIGO = RAIZ / "app"
CANON = CODIGO / "canon"

ESCRITURAS = re.compile(r"\b(INSERT\s+INTO|UPDATE|DELETE\s+FROM)\b", re.IGNORECASE)

# Tablas del canon (Capa 2). Solo `canon/` las escribe.
TABLAS_DEL_CANON = {
    "hecho_canonico",
    "snapshot_mundo",
    "hecho_snapshot",
    "estado_epistemico",
    "ironia_dramatica",
    "promesa_narrativa",
    "escena_promesa",
    "revelacion",
    "contradiccion",
    "retcon",
}


def _modulos() -> list[Path]:
    return sorted(CODIGO.rglob("*.py"))


def _literales(nodo: ast.AST) -> list[str]:
    return [
        hijo.value
        for hijo in ast.walk(nodo)
        if isinstance(hijo, ast.Constant) and isinstance(hijo.value, str)
    ]


def _abre_transaccion(funcion: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(
        isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Name)
        and nodo.func.id == "transaccion"
        for nodo in ast.walk(funcion)
    )


def _llamadas(funcion: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    return {
        nodo.func.id
        for nodo in ast.walk(funcion)
        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name)
    }


def test_toda_escritura_al_canon_ocurre_en_transaccion() -> None:
    """A-17, RNF-02.

    Una funcion que escribe cumple de dos maneras: abriendo la transaccion ella
    misma, o siendo un ayudante al que **solo** llaman funciones que la abren.
    La segunda no es una excepcion de cortesia — se comprueba call site a call
    site, y un ayudante llamado desde fuera de una transaccion suspende igual.
    SQLite no anida transacciones, asi que sin esto la unica forma de pasar la
    regla seria una funcion gigante.

    El punto ciego declarado se asume: ve la transaccion abierta, no su alcance.
    Una que se cierra antes de la ultima escritura pasa el analisis.
    """
    fuente = (CANON / "repository.py").read_text(encoding="utf-8")
    arbol = ast.parse(fuente, "repository.py")
    funciones = {
        nodo.name: nodo
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef)
    }

    incumplen: list[str] = []
    for nombre, funcion in funciones.items():
        if not any(ESCRITURAS.search(texto) for texto in _literales(funcion)):
            continue
        if _abre_transaccion(funcion):
            continue
        llamantes = [otra for otra in funciones.values() if nombre in _llamadas(otra)]
        if llamantes and all(_abre_transaccion(otra) for otra in llamantes):
            continue
        incumplen.append(f"canon/repository.py:{funcion.lineno} {nombre}")
    assert incumplen == []


def test_las_escrituras_al_canon_estan_todas_en_canon() -> None:
    """A-26. Ningun agente ni ninguna otra feature escribe el canon."""
    incumplen: list[str] = []
    for fichero in _modulos():
        if CANON in fichero.parents:
            continue
        arbol = ast.parse(fichero.read_text(encoding="utf-8"), str(fichero))
        for texto in _literales(arbol):
            if not ESCRITURAS.search(texto):
                continue
            tocadas = {t for t in TABLAS_DEL_CANON if re.search(rf"\b{t}\b", texto)}
            if tocadas:
                incumplen.append(f"{fichero.relative_to(RAIZ)}: {sorted(tocadas)}")
    assert incumplen == []


def test_ninguna_feature_importa_el_repositorio_de_otra() -> None:
    """A-26, A-24, RD-04. El servicio es el contrato; el repositorio, un detalle."""
    incumplen: list[str] = []
    for fichero in _modulos():
        partes = fichero.relative_to(CODIGO).parts
        if len(partes) < 2 or partes[0] == "commons":
            continue
        propia = partes[0]
        arbol = ast.parse(fichero.read_text(encoding="utf-8"), str(fichero))
        for nodo in ast.walk(arbol):
            modulos: list[str] = []
            if isinstance(nodo, ast.Import):
                modulos = [alias.name for alias in nodo.names]
            elif isinstance(nodo, ast.ImportFrom):
                nombres = [alias.name for alias in nodo.names]
                modulos = [f"{nodo.module}.{n}" for n in nombres] if nodo.module else []
            for modulo in modulos:
                trozos = modulo.split(".")
                if (
                    len(trozos) >= 3
                    and trozos[0] == "app"
                    and trozos[1] != propia
                    and trozos[1] != "commons"
                    and "repository" in trozos
                ):
                    incumplen.append(f"{fichero.relative_to(RAIZ)}:{nodo.lineno} {modulo}")
    assert incumplen == []
