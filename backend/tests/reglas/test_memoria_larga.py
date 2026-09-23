"""H7 · prueba 3, por analisis estatico — RF-FIND-04, P-21.

«La consolidacion es el **unico** punto de promocion de memoria de corto a largo
plazo, y ningun otro camino escribe en memoria larga.» Eso afirma algo sobre
todo el codigo, no sobre un camino, asi que se comprueba mirando el fuente: una
prueba de comportamiento diria que la via que ejercita cumple y callaria sobre
las demas.

Ese punto tiene **dos escrituras y no dos puntos**: `canon/` escribe el canon
dentro de la transaccion, y acto seguido el extractor deja sus hallazgos en
`findings/`. Lo que se verifica aqui es que no haya una tercera.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CODIGO = RAIZ / "app"
FINDINGS = CODIGO / "findings"

ESCRITURAS = re.compile(r"\b(INSERT\s+INTO|UPDATE|DELETE\s+FROM)\b", re.IGNORECASE)

# Las dos tablas de memoria larga del modo hibrido.
TABLAS_DE_HALLAZGOS = {"hallazgo", "extraccion"}


def _modulos() -> list[Path]:
    return sorted(CODIGO.rglob("*.py"))


def _literales(fichero: Path) -> list[str]:
    arbol = ast.parse(fichero.read_text(encoding="utf-8"), str(fichero))
    return [
        nodo.value
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str)
    ]


def test_solo_findings_escribe_los_hallazgos() -> None:
    """Si otra feature los escribiera, habria un segundo punto de promocion."""
    incumplen: list[str] = []
    for fichero in _modulos():
        if FINDINGS in fichero.parents:
            continue
        for texto in _literales(fichero):
            if not ESCRITURAS.search(texto):
                continue
            tocadas = {t for t in TABLAS_DE_HALLAZGOS if re.search(rf"\b{t}\b", texto)}
            if tocadas:
                incumplen.append(f"{fichero.relative_to(RAIZ)}: {sorted(tocadas)}")
    assert incumplen == []


def test_el_contexto_no_sabe_que_es_un_hallazgo() -> None:
    """P-21, el punto ciego declarado, cerrado por construccion.

    Un hallazgo `propuesto` no puede colarse en el contexto de la escena
    siguiente si la feature que ensambla el contexto no tiene forma de leerlo.
    Lo que si entra es el hecho canonico o la promesa en que el autor lo
    convirtio, y eso entra por `canon/`, como todo el canon.
    """
    contexto = CODIGO / "context"
    fuentes = sorted(contexto.rglob("*.py"))
    assert fuentes, "no hay codigo de context/ que inspeccionar"

    incumplen = [
        f"{fichero.relative_to(RAIZ)}: {tabla}"
        for fichero in fuentes
        for tabla in TABLAS_DE_HALLAZGOS
        for texto in _literales(fichero)
        if re.search(rf"\b{tabla}\b", texto)
    ]
    assert incumplen == []

    importa = [
        fichero.relative_to(RAIZ).as_posix()
        for fichero in fuentes
        if "app.findings" in fichero.read_text(encoding="utf-8")
    ]
    assert importa == []


def test_ningun_hallazgo_nace_fuera_de_una_extraccion() -> None:
    """`Extraccion propone Hallazgo`: la relacion es obligatoria, no opcional.

    La columna es `NOT NULL` con clave foranea, asi que el esquema ya lo impide.
    Esto comprueba lo otro: que no exista un `INSERT` en `hallazgo` que no venga
    de la funcion que guarda una extraccion.
    """
    arbol = ast.parse((FINDINGS / "repository.py").read_text(encoding="utf-8"), "repository.py")
    insertan = [
        funcion.name
        for funcion in ast.walk(arbol)
        if isinstance(funcion, ast.FunctionDef | ast.AsyncFunctionDef)
        and any(
            isinstance(nodo, ast.Constant)
            and isinstance(nodo.value, str)
            and re.search(r"INSERT\s+(OR\s+IGNORE\s+)?INTO\s+hallazgo\b", nodo.value, re.I)
            for nodo in ast.walk(funcion)
        )
    ]
    assert insertan == ["guardar_extraccion"]


def test_el_estado_inicial_del_hallazgo_lo_fija_el_esquema() -> None:
    """Que nazca `propuesto` no puede depender de que el codigo se acuerde.

    Es el ultimo cortafuegos de la resistencia a inyeccion: el `DEFAULT` esta en
    la migracion, y el `INSERT` no menciona la columna de estado.
    """
    migracion = (CODIGO / "commons" / "db" / "migrations" / "007_hallazgos.sql").read_text(
        encoding="utf-8"
    )
    assert "DEFAULT 'propuesto'" in migracion

    fuente = (FINDINGS / "repository.py").read_text(encoding="utf-8")
    inicio = fuente.index("INSERT OR IGNORE INTO hallazgo")
    insercion = fuente[inicio : fuente.index(")", inicio)]
    assert "estado" not in insercion, "el insert fija el estado y el esquema deja de mandar"
