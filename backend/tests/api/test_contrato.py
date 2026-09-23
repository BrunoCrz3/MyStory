"""H8 · pruebas 1 y 2 — A-13, A-24, RI-01, RI-02, RI-03.

El OpenAPI **es** el contrato: de el se deriva el cliente tipado del frontend,
que queda fuera de v1. Por eso lo que se verifica aqui no es que el endpoint
responda, sino que el contrato diga lo que tiene que decir.

La superficie minima se lee de la tabla de `spec.md` §4 y se escribe a mano en
esta prueba. Leerla del propio codigo diria solo que el codigo es igual a si
mismo; escribirla aqui la convierte en lo que es: un acuerdo que hay que romper
a proposito para que falle.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parents[2]
CODIGO = RAIZ / "app"

# Las seis features con router en v1. `replanning/` queda fuera del corte
# (spec §1.3), y por eso no esta ni en la lista ni en `main.py`.
FEATURES = ("novel", "canon", "context", "quality", "process", "findings")

# Superficie minima por feature, `spec.md` §4. Se nombra un endpoint por cada
# capacidad que la tabla enumera; que haya mas no rompe el acuerdo, que falte
# uno si.
SUPERFICIE_MINIMA = {
    "novel": [
        ("post", "/novel/obra"),
        ("post", "/novel/partes"),
        ("post", "/novel/capitulos"),
        ("post", "/novel/escenas"),
        ("post", "/novel/personajes"),
        ("get", "/novel/eventos/{evento_id}/escenas"),
    ],
    "canon": [
        ("get", "/canon/escenas/{escena_id}/snapshot"),
        ("get", "/canon/escenas/{escena_id}/hechos"),
        ("get", "/canon/personajes/{personaje_id}/conocimiento"),
        ("get", "/canon/escenas/{escena_id}/promesas-abiertas"),
        ("post", "/canon/contradicciones/deteccion"),
        ("post", "/canon/consolidaciones"),
        ("get", "/canon/hechos/{hecho_id}/retcon-simulado"),
    ],
    "context": [
        ("post", "/context/ensamblados"),
        ("get", "/context/presupuesto"),
    ],
    "quality": [
        ("post", "/quality/continuidad"),
        ("post", "/quality/criticas"),
        ("get", "/quality/escenas/{escena_id}/criticas"),
    ],
    "process": [
        ("post", "/process/briefs"),
        ("post", "/process/escenas/{escena_id}/borradores"),
        ("get", "/process/escenas/{escena_id}/versiones"),
        ("post", "/process/escenas/{escena_id}/aceptacion"),
        ("get", "/process/escenas/{escena_id}/registros"),
    ],
    "findings": [
        ("get", "/findings/escenas/{escena_id}/hallazgos"),
        ("post", "/findings/hallazgos/{hallazgo_id}/decision"),
    ],
}


def test_el_openapi_se_publica_en_openapi_json(cliente: TestClient) -> None:
    """RI-03."""
    respuesta = cliente.get("/openapi.json")
    assert respuesta.status_code == 200
    contrato = respuesta.json()
    assert contrato["openapi"].startswith("3.")
    assert contrato["info"]["title"] == "MyStory"
    assert contrato["paths"], "un contrato sin rutas no es un contrato"


def test_el_openapi_expone_la_superficie_minima_de_cada_feature(cliente: TestClient) -> None:
    """RI-01, y la tabla de `spec.md` §4 endpoint a endpoint."""
    paths: dict[str, Any] = cliente.get("/openapi.json").json()["paths"]

    faltan = [
        f"{metodo.upper()} {ruta}"
        for endpoints in SUPERFICIE_MINIMA.values()
        for metodo, ruta in endpoints
        if ruta not in paths or metodo not in paths[ruta]
    ]
    assert faltan == [], f"la superficie minima de spec.md §4 esta incompleta: {faltan}"


def test_cada_feature_tiene_su_router_y_se_monta_en_main() -> None:
    """RI-01: un router por feature, montados en `main.py`.

    Se mira el fuente y no el OpenAPI: una feature cuyo router existe pero nadie
    monta no aparece en el contrato, y entonces la prueba de arriba no diria que
    falta un router, diria que faltan endpoints.
    """
    for feature in FEATURES:
        assert (CODIGO / feature / "router.py").is_file(), feature

    main = (CODIGO / "main.py").read_text(encoding="utf-8")
    sin_montar = [feature for feature in FEATURES if f"app.{feature}.router" not in main]
    assert sin_montar == [], sin_montar
    assert main.count("include_router") == len(FEATURES)


def test_cada_ruta_pertenece_al_prefijo_de_su_feature(cliente: TestClient) -> None:
    """Un endpoint de una feature colgado del prefijo de otra hace que el
    cliente tipado se organice al reves que el backend."""
    paths = cliente.get("/openapi.json").json()["paths"]
    prefijos = {f"/{feature}" for feature in FEATURES}
    sueltas = [
        ruta
        for ruta in paths
        if ruta != "/salud" and not any(ruta.startswith(prefijo) for prefijo in prefijos)
    ]
    assert sueltas == [], sueltas


# --- A-13: sin dicts sueltos cruzando capas -------------------------------

# Modulos que forman el contrato de una feature. `models.py` y `schemas.py` son
# el contrato mismo; `service.py` y `repository.py` son las fronteras internas
# que lo transportan.
CAPAS = ("router.py", "schemas.py", "models.py", "service.py", "repository.py")

# Anotaciones que renuncian a decir que cruza. `Any` no dice nada; `object` dice
# «algo», que es lo mismo.
RENUNCIAS = {"Any", "object"}


def _anotaciones(fichero: Path) -> list[tuple[int, str]]:
    """Las anotaciones de la firma de cada funcion publica del modulo."""
    arbol = ast.parse(fichero.read_text(encoding="utf-8"), str(fichero))
    encontradas: list[tuple[int, str]] = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if nodo.name.startswith("_"):
            continue
        piezas = [argumento.annotation for argumento in nodo.args.args]
        piezas += [argumento.annotation for argumento in nodo.args.kwonlyargs]
        piezas.append(nodo.returns)
        for pieza in piezas:
            if pieza is not None:
                encontradas.append((nodo.lineno, ast.unparse(pieza)))
    return encontradas


def test_todo_esquema_de_entrada_y_salida_es_pydantic() -> None:
    """A-13, RI-02.

    Lo que se comprueba es que ninguna firma publica de una capa renuncie a
    decir que cruza. Un `dict[str, Any]` obliga a quien lo recibe a adivinar las
    claves y a convertir cada valor a mano, y el dia que una clave cambie no
    falla el tipo: falla la escena.

    El punto ciego esta declarado en A-13 y se asume: un modelo Pydantic con un
    campo `Any` dentro pasa el tipo y no dice nada. Esto mira las firmas, y el
    comprobador de tipos mira el resto.
    """
    incumplen: list[str] = []
    for feature in FEATURES:
        for nombre in CAPAS:
            fichero = CODIGO / feature / nombre
            if not fichero.is_file():
                continue
            for linea, anotacion in _anotaciones(fichero):
                tokens = set(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", anotacion))
                if tokens & RENUNCIAS:
                    incumplen.append(f"{feature}/{nombre}:{linea} {anotacion}")
    assert incumplen == [], f"contratos que no dicen que cruza: {incumplen}"


def test_ningun_mapa_del_contrato_tiene_clave_sin_tipo() -> None:
    """Un `dict` a secas es un `dict[Any, Any]` con mejor aspecto."""
    incumplen: list[str] = []
    for feature in FEATURES:
        for nombre in CAPAS:
            fichero = CODIGO / feature / nombre
            if not fichero.is_file():
                continue
            for linea, anotacion in _anotaciones(fichero):
                if re.search(r"\b(dict|list|set|tuple)\b(?!\[)", anotacion):
                    incumplen.append(f"{feature}/{nombre}:{linea} {anotacion}")
    assert incumplen == [], incumplen


# --- A-24: la logica de dominio no vive en los routers --------------------


def test_los_routers_no_importan_ningun_repositorio() -> None:
    """A-24, RD-02.

    El router traduce HTTP. Si llama al repositorio esquiva al servicio, que es
    donde vive la regla, y abre una segunda via por la que manana entrara una.

    El punto ciego esta declarado y se asume: esto mide importaciones, no
    contenido. Un `router.py` con veinte lineas de reglas y ninguna importacion
    rara pasa.
    """
    incumplen: list[str] = []
    for feature in FEATURES:
        fuente = (CODIGO / feature / "router.py").read_text(encoding="utf-8")
        arbol = ast.parse(fuente, f"{feature}/router.py")
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom):
                nombres = [alias.name for alias in nodo.names]
                if "repository" in nombres or (nodo.module or "").endswith("repository"):
                    incumplen.append(f"{feature}/router.py:{nodo.lineno}")
    assert incumplen == [], incumplen


def test_cada_endpoint_delega_en_su_servicio() -> None:
    """La otra mitad de A-24, tan lejos como el analisis estatico llega.

    Cada funcion de endpoint llama al servicio de su feature. No dice que no
    haya reglas dentro --eso es el punto ciego-- pero si que no haya endpoints
    que resuelvan por su cuenta sin pasar por el.
    """
    sin_servicio: list[str] = []
    for feature in FEATURES:
        arbol = ast.parse(
            (CODIGO / feature / "router.py").read_text(encoding="utf-8"),
            f"{feature}/router.py",
        )
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if not any(
                isinstance(decorador, ast.Call)
                and isinstance(decorador.func, ast.Attribute)
                and isinstance(decorador.func.value, ast.Name)
                and decorador.func.value.id == "router"
                for decorador in nodo.decorator_list
            ):
                continue
            if not any(
                isinstance(hijo, ast.Attribute)
                and isinstance(hijo.value, ast.Name)
                and hijo.value.id == "service"
                for hijo in ast.walk(nodo)
            ):
                sin_servicio.append(f"{feature}/router.py:{nodo.name}")
    assert sin_servicio == [], sin_servicio
