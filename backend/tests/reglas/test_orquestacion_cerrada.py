"""H6 · prueba 2 y 7, por analisis estatico — A-45, P-19, P-32, RD-05, RD-08, RD-09.

Cuatro afirmaciones que hablan de **todo** el codigo, no de un camino, y por eso
no se verifican ejecutando: una prueba de comportamiento diria que el camino que
ejercita cumple, y callaria sobre los demas.

- **Un agente no invoca a otro ni elige el siguiente paso** (P-32). Se comprueba
  por importaciones: quien no puede importar el orquestador no puede
  preguntarle ni saltarselo.
- **`registrar-generacion` corre en toda llamada al modelo** (A-45). Se comprueba
  por la forma: hay **una** puerta, y escribe la fila.
- **Solo el autor humano acepta** (P-19). Se comprueba contando quien puede
  pronunciar `ModoDeAceptacion.HUMANA`.
- **El avance del ciclo no vive en memoria** (RD-09). Se comprueba que el
  orquestador no guarda nada entre llamadas.

Las tres ultimas son lo que hara que insertar la cola de trabajos mas adelante
--hoy sincrona y en proceso, RD-05-- no toque a ningun agente.
"""

from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CODIGO = RAIZ / "app"
PROCESO = CODIGO / "process"

# El arranque no es un agente: es el sitio donde se montan los routers y se
# crean los semaforos del proceso. Alguien tiene que conocer todas las piezas, y
# que sea uno solo y declarado es justo la diferencia.
COMPOSICION = CODIGO / "main.py"

PUERTA_DEL_MODELO = "_generar_con_registro"


def _modulos() -> list[Path]:
    return sorted(CODIGO.rglob("*.py"))


def _arboles() -> list[tuple[Path, ast.Module]]:
    return [(f, ast.parse(f.read_text(encoding="utf-8"), str(f))) for f in _modulos()]


def _importados(arbol: ast.Module) -> list[str]:
    modulos: list[str] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos += [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            modulos.append(nodo.module)
            modulos += [f"{nodo.module}.{alias.name}" for alias in nodo.names]
    return modulos


def _funciones(arbol: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    return {
        nodo.name: nodo
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef)
    }


def _que_funcion(arbol: ast.Module, linea: int) -> str | None:
    """A que funcion pertenece una linea. Sirve para localizar una llamada."""
    encontrada: str | None = None
    for nombre, nodo in _funciones(arbol).items():
        fin = nodo.end_lineno or nodo.lineno
        if nodo.lineno <= linea <= fin:
            encontrada = nombre
    return encontrada


def test_ningun_agente_invoca_a_otro() -> None:
    """P-32, RD-08.

    Los pasos del ciclo viven en `quality/`, `context/`, `canon/` y `findings/`
    cuando llegue. Ninguno importa `process/`, asi que ninguno puede llamar al
    siguiente ni preguntar cual es: el contrato de agente queda cerrado por
    construccion y no por disciplina.
    """
    incumplen: list[str] = []
    for fichero, arbol in _arboles():
        if PROCESO in fichero.parents or fichero == COMPOSICION:
            continue
        for modulo in _importados(arbol):
            if modulo.startswith("app.process"):
                incumplen.append(f"{fichero.relative_to(RAIZ)}: {modulo}")
    assert incumplen == [], (
        "un modulo de fuera de process/ conoce al orquestador: puede elegir el siguiente paso"
    )


def test_el_orquestador_elige_y_nadie_mas_lo_consulta() -> None:
    """`siguiente_paso` solo se nombra donde se define y donde se sirve."""
    permitidos = {PROCESO / "orquestador.py", PROCESO / "service.py"}
    nombran = {
        fichero
        for fichero, arbol in _arboles()
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Name) and nodo.id == "siguiente_paso"
    }
    assert nombran <= permitidos, f"alguien mas decide el siguiente paso: {sorted(nombran)}"


def test_solo_hay_una_puerta_que_llama_al_modelo() -> None:
    """A-45, primera mitad.

    La garantia de que `registrar-generacion` corre siempre no es acordarse de
    llamarla: es que no exista una segunda via por la que olvidarla.
    """
    fuera: list[str] = []
    for fichero, arbol in _arboles():
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call) or not isinstance(nodo.func, ast.Attribute):
                continue
            if nodo.func.attr != "generar":
                continue
            if fichero == PROCESO / "service.py" and _que_funcion(arbol, nodo.lineno) in {
                PUERTA_DEL_MODELO
            }:
                continue
            fuera.append(f"{fichero.relative_to(RAIZ)}:{nodo.lineno}")
    assert fuera == [], f"llamadas al modelo fuera de la unica puerta: {fuera}"


def test_la_puerta_del_modelo_registra_la_generacion() -> None:
    """A-45, segunda mitad. La fila se escribe en la misma funcion que llama.

    El punto ciego declarado se asume: garantiza la fila, no su contenido. Un
    registro con el prompt truncado o el contexto sin serializar cumple igual, y
    de eso se ocupa la prueba de comportamiento en `tests/process/`.
    """
    arbol = ast.parse((PROCESO / "service.py").read_text(encoding="utf-8"), "service.py")
    puerta = _funciones(arbol)[PUERTA_DEL_MODELO]
    escribe = [
        nodo
        for nodo in ast.walk(puerta)
        if isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Attribute)
        and nodo.func.attr == "insertar_registro"
    ]
    assert len(escribe) == 1, "la puerta que llama al modelo no deja registro de generacion"


def test_la_llamada_al_proveedor_vive_solo_en_commons() -> None:
    """`commons/` no sabe que es una escena, y ninguna feature sabe que hay un SDK."""
    fuera = [
        f"{fichero.relative_to(RAIZ)}:{nodo.lineno}"
        for fichero, arbol in _arboles()
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Attribute)
        and isinstance(nodo.func.value, ast.Attribute)
        and nodo.func.value.attr == "messages"
        and fichero.parent != CODIGO / "commons" / "llm"
        and fichero.parent != CODIGO / "commons" / "tokens"
    ]
    assert fuera == []


def test_solo_una_funcion_puede_aceptar_una_escena() -> None:
    """P-19, RF-PROC-07.

    `ModoDeAceptacion.HUMANA` es la llave de la transicion a `aceptada`. Que solo
    una funcion la pronuncie es lo que convierte el guardarrail en una puerta y
    no en una costumbre.
    """
    pronuncian: list[str] = []
    for fichero, arbol in _arboles():
        for nodo in ast.walk(arbol):
            if (
                isinstance(nodo, ast.Attribute)
                and nodo.attr == "HUMANA"
                and isinstance(nodo.value, ast.Name)
                and nodo.value.id == "ModoDeAceptacion"
            ):
                ruta = fichero.relative_to(RAIZ).as_posix()
                pronuncian.append(f"{ruta}:{_que_funcion(arbol, nodo.lineno)}")

    # Dos sitios y solo dos: el guardarrail, que compara, y la puerta, que pasa
    # la llave. Cualquier tercero seria una segunda forma de aceptar.
    assert sorted(pronuncian) == [
        "app/novel/service.py:transicionar_escena",
        "app/process/service.py:aceptar_escena",
    ], pronuncian


def test_el_orquestador_no_guarda_el_avance_en_memoria() -> None:
    """RD-09.

    El estado del ciclo se deduce del estado de la escena en la base. Una
    variable de modulo mutable en el orquestador seria exactamente la pila de
    llamadas que la regla prohibe, y el dia que se encole la cola, el punto del
    ciclo se perderia en cada reinicio.
    """
    arbol = ast.parse((PROCESO / "orquestador.py").read_text(encoding="utf-8"), "orquestador.py")
    mutables = [
        objetivo.id
        for nodo in arbol.body
        if isinstance(nodo, ast.Assign)
        for objetivo in nodo.targets
        if isinstance(objetivo, ast.Name) and isinstance(nodo.value, ast.Dict | ast.List | ast.Set)
    ]
    assert mutables == [], f"el orquestador guarda estado entre llamadas: {mutables}"


def test_v1_no_persiste_cola_de_trabajos() -> None:
    """RD-05. El trabajo encolado es infraestructura y no se ratifica en la
    ontologia; en v1 ni siquiera existe como tabla."""
    migraciones = sorted((CODIGO / "commons" / "db" / "migrations").glob("*.sql"))
    sospechosas = [
        migracion.name
        for migracion in migraciones
        if "CREATE TABLE trabajo" in migracion.read_text(encoding="utf-8")
        or "CREATE TABLE job" in migracion.read_text(encoding="utf-8")
    ]
    assert sospechosas == []
