"""Reglas propias que CI vigila en cada commit.

Las filas A-02, A-12, A-35, A-37 y A-40 de `docs/verification.md` se verifican
por analisis estatico, no por prueba de comportamiento: lo que afirman es una
propiedad del codigo fuente, y una prueba que ejecuta un camino concreto no
dice nada de los demas. RD-07 y RNF-11 van aqui por lo mismo.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
CODIGO = RAIZ / "app"
REPOSITORIO = RAIZ.parent
UMBRALES = REPOSITORIO / "config" / "thresholds.yaml"

PETICIONES_AL_MODELO = {"create", "stream", "count_tokens"}


def _modulos() -> list[Path]:
    return sorted(CODIGO.rglob("*.py"))


def _arboles() -> list[tuple[Path, ast.Module]]:
    return [(f, ast.parse(f.read_text(encoding="utf-8"), str(f))) for f in _modulos()]


def _es_peticion_al_modelo(nodo: ast.AST) -> bool:
    if not isinstance(nodo, ast.Call) or not isinstance(nodo.func, ast.Attribute):
        return False
    if nodo.func.attr not in PETICIONES_AL_MODELO:
        return False
    receptor = nodo.func.value
    return isinstance(receptor, ast.Attribute) and receptor.attr == "messages"


def _funciones(arbol: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [n for n in ast.walk(arbol) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]


def test_el_contador_de_tokens_corre_antes_de_la_llamada() -> None:
    """A-02, RF-CTX-03. Contar despues es contar el gasto, no decidir."""
    incumplen: list[str] = []
    for fichero, arbol in _arboles():
        for funcion in _funciones(arbol):
            peticiones = [n for n in ast.walk(funcion) if _es_peticion_al_modelo(n)]
            generaciones = [
                n
                for n in peticiones
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and n.func.attr != "count_tokens"
            ]
            if not generaciones:
                continue
            recuentos = [
                n
                for n in ast.walk(funcion)
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and n.func.attr in {"contar", "count_tokens"}
            ]
            primera_generacion = min(n.lineno for n in generaciones)
            if not any(n.lineno < primera_generacion for n in recuentos):
                incumplen.append(f"{fichero.relative_to(RAIZ)}:{funcion.lineno} {funcion.name}")
    assert incumplen == []


def test_toda_llamada_al_modelo_lleva_timeout_explicito() -> None:
    """A-35, RI-06. Un timeout implicito es un cuelgue esperando a ocurrir."""
    incumplen: list[str] = []
    for fichero, arbol in _arboles():
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call) or not _es_peticion_al_modelo(nodo):
                continue
            if not any(clave.arg == "timeout" for clave in nodo.keywords):
                incumplen.append(f"{fichero.relative_to(RAIZ)}:{nodo.lineno}")
    assert incumplen == []


def test_toda_llamada_al_modelo_es_asincrona() -> None:
    """A-35, RI-06. El trabajo largo corre dentro de este mismo proceso."""
    incumplen: list[str] = []
    for fichero, arbol in _arboles():
        esperadas = {id(n.value) for n in ast.walk(arbol) if isinstance(n, ast.Await)}
        for nodo in ast.walk(arbol):
            if _es_peticion_al_modelo(nodo) and id(nodo) not in esperadas:
                incumplen.append(f"{fichero.relative_to(RAIZ)}:{nodo.lineno}")
    assert incumplen == []


def test_ningun_camino_ejecuta_lo_que_devuelve_el_modelo() -> None:
    """A-12, spec 001 seccion 9.8. La salida del redactor es prosa que se guarda.

    Se mira el arbol, no el texto: `re.compile` no es `compile`, y una regla que
    no sabe distinguirlos acaba desactivada por ruido.
    """
    prohibidas = {"eval", "exec", "compile", "system", "popen", "run", "loads", "load"}
    modulos_prohibidos = {"subprocess", "os", "pickle", "marshal", "shelve"}

    incumplen: list[str] = []
    for fichero, arbol in _arboles():
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import | ast.ImportFrom):
                nombres = (
                    [a.name for a in nodo.names]
                    if isinstance(nodo, ast.Import)
                    else [nodo.module or ""]
                )
                for nombre in nombres:
                    if nombre.split(".")[0] in modulos_prohibidos - {"os"}:
                        incumplen.append(f"{fichero.relative_to(RAIZ)}:{nodo.lineno} {nombre}")
            if (
                isinstance(nodo, ast.Call)
                and isinstance(nodo.func, ast.Name)
                and nodo.func.id in {"eval", "exec", "compile"}
            ):
                incumplen.append(f"{fichero.relative_to(RAIZ)}:{nodo.lineno} {nodo.func.id}")
            if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute):
                receptor = nodo.func.value
                if (
                    isinstance(receptor, ast.Name)
                    and receptor.id in modulos_prohibidos
                    and nodo.func.attr in prohibidas
                ):
                    incumplen.append(
                        f"{fichero.relative_to(RAIZ)}:{nodo.lineno} {receptor.id}.{nodo.func.attr}"
                    )
    assert incumplen == []


def test_el_stack_cerrado_no_admite_dependencias_vetadas() -> None:
    """A-37, RNF-08, RD-06. La lista sale de AGENTS.md, Requisitos tecnicos."""
    vetadas = {
        "sqlalchemy",
        "sqlmodel",
        "alembic",
        "django",
        "flask",
        "tortoise-orm",
        "peewee",
        "psycopg",
        "psycopg2",
        "asyncpg",
        "pgvector",
        "pinecone",
        "chromadb",
        "redis",
        "celery",
        "kombu",
    }
    fuentes = [RAIZ / "pyproject.toml"]
    if (RAIZ / "uv.lock").exists():
        fuentes.append(RAIZ / "uv.lock")

    encontradas: set[str] = set()
    for fuente in fuentes:
        texto = fuente.read_text(encoding="utf-8").lower()
        for vetada in vetadas:
            if re.search(r"(?<![a-z0-9_-])" + re.escape(vetada) + r"(?![a-z0-9_-])", texto):
                encontradas.add(vetada)
    assert encontradas == set()


def test_ninguna_cifra_de_thresholds_esta_escrita_suelta_en_el_codigo() -> None:
    """A-40, RNF-14. Si un numero esta en el codigo y en el fichero, sobra en el codigo."""
    estructurales = {0.0, 1.0, 2.0, -1.0}
    cifras: set[float] = set()

    def recoger(valor: object) -> None:
        if isinstance(valor, bool) or valor is None:
            return
        if isinstance(valor, int | float):
            cifras.add(float(valor))
        elif isinstance(valor, dict):
            for hijo in valor.values():
                recoger(hijo)
        elif isinstance(valor, list):
            for hijo in valor:
                recoger(hijo)

    recoger(yaml.safe_load(UMBRALES.read_text(encoding="utf-8")))
    cifras -= estructurales

    incumplen: list[str] = []
    for fichero, arbol in _arboles():
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Constant):
                continue
            if isinstance(nodo.value, bool) or not isinstance(nodo.value, int | float):
                continue
            if float(nodo.value) in cifras:
                incumplen.append(f"{fichero.relative_to(RAIZ)}:{nodo.lineno} {nodo.value}")
    assert incumplen == []


def test_no_hay_mocks_en_el_codigo_de_produccion() -> None:
    """RD-07, AGENTS.md regla 8: ni siquiera temporales."""
    senales = ("unittest.mock", "MagicMock", "monkeypatch", "FakeClient", "StubCliente")
    incumplen = [
        f"{fichero.relative_to(RAIZ)}: {senal}"
        for fichero in _modulos()
        for senal in senales
        if senal in fichero.read_text(encoding="utf-8")
    ]
    assert incumplen == []


def test_ninguna_tabla_lleva_user_id_ni_tenant_id() -> None:
    """RNF-11. Una segunda novela es otra instancia, no una columna mas."""
    migraciones = sorted((CODIGO / "commons" / "db" / "migrations").glob("*.sql"))
    assert migraciones, "no hay migraciones que inspeccionar"
    incumplen = [
        migracion.name
        for migracion in migraciones
        if re.search(r"\b(user_id|tenant_id)\b", _sin_comentarios(migracion))
    ]
    assert incumplen == []


def _sin_comentarios(migracion: Path) -> str:
    lineas = migracion.read_text(encoding="utf-8").splitlines()
    return "\n".join(linea for linea in lineas if not linea.lstrip().startswith("--"))
