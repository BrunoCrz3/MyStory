"""Comprobaciones estáticas de la arquitectura sobre el árbol de `app/`.

Cada función recibe la carpeta raíz del paquete y devuelve la lista de violaciones, para que
las meta-pruebas puedan ejecutarlas sobre un árbol escrito a propósito con errores.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from pathlib import Path

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
RAIZ_APP = RAIZ_BACKEND / "app"
RAIZ_REPO = RAIZ_BACKEND.parent
ARQUITECTURA = RAIZ_REPO / "docs" / "architecture.md"

FEATURES = frozenset(
    {
        "intake",
        "novel",
        "canon",
        "context",
        "quality",
        "guardrail",
        "process",
        "policy",
        "versioning",
    }
)
# Paquetes que no son feature. `commons/` es infraestructura; `prompts/` y `skills/` son
# contenido que cargan los roles (architecture.md § Anatomía, D-09). Cualquier feature puede
# importarlos; ellos no importan ninguna feature.
INFRAESTRUCTURA = frozenset({"commons", "prompts", "skills"})
HOJAS = frozenset({"intake", "guardrail"})

PALABRAS_DOBLE = re.compile(r"(^|_)(doble|dobles|fake|stub|mock|mocks)(_|$)", re.IGNORECASE)
EXCLUIDOS = frozenset(
    {
        "sqlalchemy",
        "sqlmodel",
        "peewee",
        "pony",
        "tortoise-orm",
        "django",
        "flask",
        "psycopg",
        "psycopg2",
        "psycopg2-binary",
        "asyncpg",
        "pgvector",
        "pinecone",
        "pinecone-client",
        "chromadb",
        "redis",
        "celery",
        "sqlite-vec",
    }
)
TABLAS_VERSIONADAS = re.compile(r"\b(hecho|hecho_capitulo|version_capitulo|version_novela)\b")


def _modulos(raiz: Path) -> Iterator[tuple[Path, ast.Module]]:
    for fichero in sorted(raiz.rglob("*.py")):
        yield fichero, ast.parse(fichero.read_text(encoding="utf-8"), filename=str(fichero))


def _paquete(raiz: Path, fichero: Path) -> str | None:
    partes = fichero.relative_to(raiz).parts
    return partes[0] if len(partes) > 1 else None


def _importaciones(arbol: ast.Module) -> Iterator[str]:
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                yield alias.name
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            yield nodo.module
            for alias in nodo.names:
                yield f"{nodo.module}.{alias.name}"


def aristas_permitidas(arquitectura: Path = ARQUITECTURA) -> set[tuple[str, str]]:
    """Lee el diagrama de § Regla de importación de `docs/architecture.md`."""
    texto = arquitectura.read_text(encoding="utf-8")
    bloque = texto.split("**Regla de importación.**", 1)[1].split("```mermaid", 1)[1]
    bloque = bloque.split("```", 1)[0]
    nombres = dict(re.findall(r"(\w+)\[(\w+)/?\]", bloque))
    aristas = set()
    for origen, destino in re.findall(r"(\w+)(?:\[[^\]]*\])?\s*-->\s*(\w+)", bloque):
        aristas.add((nombres[origen], nombres[destino]))
    return aristas


def violaciones_importacion(
    raiz: Path = RAIZ_APP, permitidas: set[tuple[str, str]] | None = None
) -> list[str]:
    permitidas = aristas_permitidas() if permitidas is None else permitidas
    problemas: list[str] = []
    aristas: set[tuple[str, str]] = set()
    for fichero, arbol in _modulos(raiz):
        origen = _paquete(raiz, fichero)
        if origen is None:
            continue
        for modulo in _importaciones(arbol):
            partes = modulo.split(".")
            if partes[0] != "app" or len(partes) < 2 or partes[1] == origen:
                continue
            destino = partes[1]
            if origen in INFRAESTRUCTURA and destino in FEATURES:
                problemas.append(
                    f"{fichero.name}: {origen}/ no puede importar la feature {destino}/"
                )
            if destino not in FEATURES:
                continue
            submodulo = partes[2] if len(partes) > 2 else None
            if submodulo not in (None, "service"):
                problemas.append(
                    f"{origen}/{fichero.name} importa {modulo}: de otra feature solo `service`"
                )
            if origen in FEATURES:
                aristas.add((origen, destino))
    for origen, destino in sorted(aristas):
        if origen in HOJAS:
            problemas.append(
                f"{origen}/ importa {destino}/: {origen}/ solo puede importar commons/"
            )
        elif (origen, destino) not in permitidas:
            problemas.append(f"arista {origen} -> {destino} ausente de architecture.md")
    ciclo = _ciclo(aristas)
    if ciclo:
        problemas.append("ciclo de importación: " + " -> ".join(ciclo))
    return problemas


def _ciclo(aristas: set[tuple[str, str]]) -> list[str] | None:
    grafo: dict[str, list[str]] = {}
    for a, b in aristas:
        grafo.setdefault(a, []).append(b)
    visitando: list[str] = []
    hechos: set[str] = set()

    def visitar(n: str) -> list[str] | None:
        if n in visitando:
            return [*visitando[visitando.index(n) :], n]
        if n in hechos:
            return None
        visitando.append(n)
        for m in grafo.get(n, []):
            encontrado = visitar(m)
            if encontrado:
                return encontrado
        visitando.pop()
        hechos.add(n)
        return None

    for nodo in sorted(grafo):
        encontrado = visitar(nodo)
        if encontrado:
            return encontrado
    return None


def violaciones_dobles(raiz: Path = RAIZ_APP) -> list[str]:
    problemas = []
    for fichero, arbol in _modulos(raiz):
        if PALABRAS_DOBLE.search(fichero.stem):
            problemas.append(f"{fichero}: nombre de doble en el código de producción")
        sospechosos = sorted(
            modulo
            for modulo in _importaciones(arbol)
            if modulo.startswith("unittest.mock")
            or modulo.split(".")[0] in ("mock", "tests", "pytest")
            or any(PALABRAS_DOBLE.search(p) for p in modulo.split("."))
        )
        if sospechosos:
            problemas.append(f"{fichero.name} importa dobles o pruebas: {sospechosos[0]}")
    return problemas


def paquetes_del_lock(lock: Path) -> set[str]:
    return set(re.findall(r'^name = "([^"]+)"', lock.read_text(encoding="utf-8"), re.M))


def violaciones_dependencias(lock: Path = RAIZ_BACKEND / "uv.lock") -> list[str]:
    return [f"{p}: excluido por CLAUDE.md" for p in sorted(paquetes_del_lock(lock) & EXCLUIDOS)]


def violaciones_parametros(raiz: Path = RAIZ_APP) -> list[str]:
    """RD-02: `novel_id` y `version` son obligatorios, de palabra clave y sin valor por defecto.

    Una consulta que no acota a una novela —listar todas, reclamar el siguiente trabajo— se
    declara en `CONSULTAS_TRANSVERSALES` del propio repositorio, y así queda a la vista.
    """
    problemas = []
    for fichero in sorted(raiz.rglob("repository.py")):
        texto = fichero.read_text(encoding="utf-8")
        arbol = ast.parse(texto)
        transversales: set[str] = set()
        for nodo in arbol.body:
            if (
                isinstance(nodo, ast.Assign)
                and any(
                    isinstance(t, ast.Name) and t.id == "CONSULTAS_TRANSVERSALES"
                    for t in nodo.targets
                )
                and isinstance(nodo.value, (ast.Set, ast.List, ast.Tuple))
            ):
                transversales = {
                    e.value
                    for e in nodo.value.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)
                }
        for nodo in arbol.body:
            if not isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef) or nodo.name.startswith(
                "_"
            ):
                continue
            if nodo.name in transversales:
                continue
            nombre = f"{fichero.parent.name}/repository.py::{nodo.name}"
            kw = {
                a.arg: d for a, d in zip(nodo.args.kwonlyargs, nodo.args.kw_defaults, strict=True)
            }
            for requerido in ("novel_id",):
                if requerido not in kw:
                    problemas.append(f"{nombre}: falta `{requerido}` de palabra clave")
                elif kw[requerido] is not None:
                    problemas.append(f"{nombre}: `{requerido}` no puede tener valor por defecto")
            fuente = ast.get_source_segment(texto, nodo) or ""
            if TABLAS_VERSIONADAS.search(fuente):
                if "version" not in kw:
                    problemas.append(f"{nombre}: toca tablas versionadas y le falta `version`")
                elif kw["version"] is not None:
                    problemas.append(f"{nombre}: `version` no puede tener valor por defecto")
    return problemas


def violaciones_camino_al_modelo(raiz: Path = RAIZ_APP) -> list[str]:
    """RNF-08: fuera de `commons/llm/` nadie llama a `generar` ni a `contar_tokens`.

    El único camino es `LlamadorModelo.llamar()`, que abre el span; una llamada directa al
    cliente sería una llamada al modelo sin span.
    """
    problemas = []
    permitido = raiz / "commons" / "llm"
    for fichero, arbol in _modulos(raiz):
        if permitido in fichero.parents:
            continue
        for nodo in ast.walk(arbol):
            if (
                isinstance(nodo, ast.Call)
                and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr in ("generar", "contar_tokens")
            ):
                problemas.append(f"{fichero.name}:{nodo.lineno} llama a .{nodo.func.attr}()")
    return problemas


# Lo único que lanza un proceso: el CLI del proveedor `claude_code`, con argumentos propios y
# la petición por la entrada estándar (TO-040), y `lake build` con argumentos fijos sobre un
# fichero sin texto libre de la novela (spec 4, regla 11, A-04 del plan 4). Nunca con la salida
# del modelo.
_EJECUCION_PERMITIDA = {
    ("commons/llm/claude_code.py", "anyio.run_process"),
    ("versioning/lean/ejecutar.py", "asyncio.create_subprocess_exec"),
}
_NOMBRES_PROHIBIDOS = frozenset({"eval", "exec"})
_MODULOS_PROCESO = ("subprocess.", "os.system", "os.popen", "os.exec", "os.spawn")
_LLAMADAS_PROCESO = frozenset(
    {"anyio.run_process", "anyio.open_process", "asyncio.create_subprocess_exec",
     "asyncio.create_subprocess_shell"}
)  # fmt: skip


def _nombre_llamada(nodo: ast.expr) -> str | None:
    partes: list[str] = []
    while isinstance(nodo, ast.Attribute):
        partes.append(nodo.attr)
        nodo = nodo.value
    if isinstance(nodo, ast.Name):
        partes.append(nodo.id)
        return ".".join(reversed(partes))
    return None


def violaciones_ejecucion(raiz: Path = RAIZ_APP) -> list[str]:
    """RNF-09: ningún `eval`/`exec`, ningún `os.system` y ningún proceso fuera de la lista."""
    problemas = []
    for fichero, arbol in _modulos(raiz):
        relativo = fichero.relative_to(raiz).as_posix()
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            nombre = _nombre_llamada(nodo.func)
            if nombre is None:
                continue
            prohibida = (
                nombre in _NOMBRES_PROHIBIDOS
                or nombre.startswith(_MODULOS_PROCESO)
                or nombre in _LLAMADAS_PROCESO
            )
            if prohibida and (relativo, nombre) not in _EJECUCION_PERMITIDA:
                problemas.append(f"{relativo}:{nodo.lineno} llama a {nombre}()")
    return problemas
