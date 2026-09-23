"""H5 · prueba 8 — A-49, RF-QUA-07.

«Tras cada correccion se re-ejecutan todos los validadores, no solo el que
fallo.» La garantia no es una llamada bien puesta: es que no exista la otra
via. Hay un registro y un solo camino que lo recorre entero.

El punto ciego declarado se asume: garantiza que se invoquen todos, no que cada
uno reciba el texto corregido en vez de una puntuacion en cache.
"""

from __future__ import annotations

import ast
from pathlib import Path

from app.quality import dimensiones
from app.quality.service import VALIDADORES

RAIZ = Path(__file__).resolve().parents[2]
SERVICIO = RAIZ / "app" / "quality" / "service.py"


def test_el_registro_contiene_todos_los_validadores_definidos() -> None:
    definidos = {
        nombre
        for nombre in dir(dimensiones)
        if nombre.startswith("validar_") and callable(getattr(dimensiones, nombre))
    }
    registrados = {validador.__name__ for validador in VALIDADORES}
    assert definidos == registrados, (
        f"validadores escritos y no registrados: {sorted(definidos - registrados)}"
    )


def test_solo_un_camino_recorre_el_registro() -> None:
    """Si hubiera dos, uno de ellos acabaria recorriendo menos."""
    arbol = ast.parse(SERVICIO.read_text(encoding="utf-8"), "service.py")
    recorren = [
        funcion.name
        for funcion in ast.walk(arbol)
        if isinstance(funcion, ast.FunctionDef | ast.AsyncFunctionDef)
        and any(
            isinstance(nodo, ast.Name) and nodo.id == "VALIDADORES" for nodo in ast.walk(funcion)
        )
    ]
    assert recorren == ["criticar"]


def test_ningun_validador_se_llama_por_su_nombre_fuera_del_registro() -> None:
    """Llamar a uno a mano es, exactamente, revalidar solo lo que fallo."""
    nombres = {validador.__name__ for validador in VALIDADORES}
    culpables: list[str] = []
    for fichero in sorted((RAIZ / "app").rglob("*.py")):
        arbol = ast.parse(fichero.read_text(encoding="utf-8"), str(fichero))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            llamado = getattr(nodo.func, "attr", None) or getattr(nodo.func, "id", None)
            if llamado in nombres:
                culpables.append(f"{fichero.relative_to(RAIZ)}:{nodo.lineno} {llamado}")
    assert culpables == []
