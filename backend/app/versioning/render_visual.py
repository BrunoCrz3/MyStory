"""`render_visual`: el gate pinta la versión candidata en la página `lectura` (TO-026, TO-045).

El harness es **cliente del servidor Playwright MCP con llamadas guionizadas**: navega a la
lectura de la versión (CL-01), espera a `data-estado = lista` (CL-02), extrae el DOM de una vez
con los selectores de `lectura.py` (CL-03) y lee la consola. No hay modelo en ningún punto: un
juicio de modelo en una puerta bloqueante haría irreproducible una publicación rechazada.

La extracción y la evaluación están separadas. `evaluar` es una función pura que compara lo
que la página pinta con lo que la story bible dice de la versión, y clasifica cada hallazgo
(`architecture.md` § `render_visual` en el gate): si el dato **no está** en la story bible es
un problema de datos del rol dueño; si **está** y no se pinta, es un bug de maquetación.

Sin `PLAYWRIGHT_MCP_URL` y `STORYMAKER_LECTURA_URL`, la implementación de producción es
`SinNavegador`, que falla con el motivo: sin validación visual ninguna versión se publica
(RNF-19, A-114).
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from functools import partial
from typing import Literal, Protocol

import anyio
import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.exceptions import MCPError
from pydantic import BaseModel, ConfigDict

from app.commons.config import Config
from app.commons.db import BaseDatos
from app.process.service import VeredictoGate
from app.versioning import ficha as _ficha
from app.versioning import lectura, repository
from app.versioning import portada as _portada

NOMBRE = "render_visual"


class RenderVisual(Protocol):
    async def __call__(self, *, novel_id: str, version: int) -> VeredictoGate: ...


class SinNavegador:
    """Sin servidor MCP no hay render que afirmar: el validador falla y lo dice."""

    async def __call__(self, *, novel_id: str, version: int) -> VeredictoGate:
        return VeredictoGate(
            nombre=NOMBRE,
            pasa=False,
            valor=0.0,
            detalle=(
                "no hay servidor Playwright MCP configurado (PLAYWRIGHT_MCP_URL y "
                f"STORYMAKER_LECTURA_URL): la versión {version} no se puede pintar y, sin "
                "validación visual, no se publica"
            ),
        )


# --- Aserciones ------------------------------------------------------------------------


class Asercion(BaseModel):
    """Una aserción y la tool del servidor MCP que le da la evidencia (TO-026, residuo
    declarado: lo que ninguna tool expone se declara no cubierto)."""

    model_config = ConfigDict(frozen=True)

    nombre: str
    tools: tuple[str, ...]
    que: str


ASERCIONES: tuple[Asercion, ...] = (
    Asercion(
        nombre="estado",
        tools=("browser_navigate", "browser_evaluate"),
        que="CL-02: la raíz llega a `data-estado = lista` dentro de la espera; `error` falla",
    ),
    Asercion(
        nombre="selectores",
        tools=("browser_evaluate",),
        que="CL-03: cada selector con su cardinalidad, dentro de su contenedor, y la raíz con "
        "la novela y la versión pedidas",
    ),
    Asercion(
        nombre="indice",
        tools=("browser_evaluate",),
        que="Una entrada y un capítulo por capítulo, en orden, con su título; cada enlace "
        "resuelve a `#capitulo-{n}` y la marca de modificado es exacta",
    ),
    Asercion(
        nombre="ficha",
        tools=("browser_evaluate",),
        que="Cada personaje y lugar de la ficha, con un enlace a cada capítulo donde aparece, "
        "y cada enlace resuelve",
    ),
    Asercion(
        nombre="portada",
        tools=("browser_evaluate",),
        que="La portada muestra el título y la dedicatoria",
    ),
    Asercion(
        nombre="consola",
        tools=("browser_console_messages",),
        que="Sin errores de consola",
    ),
    Asercion(
        nombre="desbordes",
        tools=("browser_evaluate",),
        que="Ninguna caja del contrato ni el documento son más anchos que su contenedor",
    ),
)
_TOOLS = {a.nombre: "+".join(a.tools) for a in ASERCIONES}


class Hallazgo(BaseModel):
    model_config = ConfigDict(frozen=True)

    asercion: str
    clase: Literal["datos", "maquetacion"]
    detalle: str

    def texto(self) -> str:
        return f"[{self.asercion} · {_TOOLS[self.asercion]}] {self.clase}: {self.detalle}"


class LecturaEsperada(BaseModel):
    """Lo que la story bible dice de la versión: lo que la página tiene que pintar."""

    novel_id: str
    version: int
    titulo: str | None
    dedicatoria: str | None
    capitulos: list[tuple[int, str | None, bool]]
    personajes: list[tuple[str, list[int]]]
    lugares: list[tuple[str, list[int]]]


class _Enlace(BaseModel):
    capitulo: str | None = None
    href: str | None = None
    resuelve: bool = False


class _Entrada(_Enlace):
    modificado: bool = False


class _CapituloDom(BaseModel):
    capitulo: str | None = None
    id: str | None = None
    titulo: str | None = None
    modificado: bool = False


class _EntradaFicha(BaseModel):
    tipo: str
    nombre: str | None = None
    enlaces: list[_Enlace] = []


class _Raiz(BaseModel):
    novel_id: str | None = None
    version: str | None = None


class _PortadaDom(BaseModel):
    titulo: str | None = None
    dedicatoria: str | None = None


class Dom(BaseModel):
    """Lo que devuelve la extracción: solo lo que las aserciones miran."""

    estado: str | None = None
    raiz: _Raiz | None = None
    cuentas: dict[str, int] = {}
    fuera: list[str] = []
    indice: list[_Entrada] = []
    capitulos: list[_CapituloDom] = []
    ficha: list[_EntradaFicha] = []
    portada: _PortadaDom = _PortadaDom()
    desbordes: list[str] = []


def cardinalidades(e: LecturaEsperada) -> dict[str, int]:
    """Cuántos elementos de cada selector pinta una lectura correcta de `e` (CL-03)."""
    n = len(e.capitulos)
    unicos = ("lectura", "portada", "portada-titulo", "portada-dedicatoria", "indice", "ficha")
    return {
        **dict.fromkeys(unicos, 1),
        **dict.fromkeys(("indice-entrada", "capitulo", "capitulo-titulo", "capitulo-texto"), n),
        "ficha-personaje": len(e.personajes),
        "ficha-lugar": len(e.lugares),
        "ficha-enlace-capitulo": sum(len(c) for _, c in e.personajes + e.lugares),
        "capitulo-modificado": 2 * sum(1 for *_, m in e.capitulos if m),
    }


def _norma(texto: str | None) -> str:
    return " ".join((texto or "").split())


def _enlace_roto(numero: str | None, e: _Enlace) -> bool:
    return not e.resuelve or e.href != f"#capitulo-{numero}"


def _indice(e: LecturaEsperada, dom: Dom) -> list[Hallazgo]:
    hallazgos: list[Hallazgo] = []

    def falla(clase: Literal["datos", "maquetacion"], detalle: str) -> None:
        hallazgos.append(Hallazgo(asercion="indice", clase=clase, detalle=detalle))

    numeros = [str(n) for n, _, _ in e.capitulos]
    if [x.capitulo for x in dom.indice] != numeros:
        falla("maquetacion", f"el índice lista {[x.capitulo for x in dom.indice]}, no {numeros}")
    if [x.capitulo for x in dom.capitulos] != numeros:
        falla("maquetacion", f"los capítulos son {[x.capitulo for x in dom.capitulos]}")
    for entrada in dom.indice:
        if _enlace_roto(entrada.capitulo, entrada):
            falla("maquetacion", f"la entrada {entrada.capitulo} enlaza a {entrada.href!r}")
    por_numero = {x.capitulo: x for x in dom.capitulos}
    entradas = {x.capitulo: x for x in dom.indice}
    for n, titulo, modificado in e.capitulos:
        pintado = por_numero.get(str(n))
        if not _norma(titulo):
            # El dato falta en la story bible: no es maquetación (O-10, A-80).
            falla(
                "datos", f"el capítulo {n} no tiene título en la story bible (rol dueño: redactor)"
            )
        elif pintado is not None and _norma(pintado.titulo) != _norma(titulo):
            falla("maquetacion", f"el capítulo {n} pinta el título {pintado.titulo!r}")
        if pintado is not None and pintado.id != f"capitulo-{n}":
            falla("maquetacion", f"el capítulo {n} tiene id {pintado.id!r}")
        for donde, x in (("el capítulo", pintado), ("la entrada del índice", entradas.get(str(n)))):
            if x is not None and x.modificado != modificado:
                falla("maquetacion", f"{donde} {n} marca modificado={x.modificado}")
    return hallazgos


def _ficha_hallazgos(e: LecturaEsperada, dom: Dom) -> list[Hallazgo]:
    hallazgos: list[Hallazgo] = []
    pintadas = {(x.tipo, x.nombre): x for x in dom.ficha}
    for tipo, entradas in (("ficha-personaje", e.personajes), ("ficha-lugar", e.lugares)):
        for nombre, capitulos in entradas:
            x = pintadas.get((tipo, nombre))
            if x is None:
                detalle = f"falta {nombre!r} en la ficha"
                hallazgos.append(Hallazgo(asercion="ficha", clase="maquetacion", detalle=detalle))
                continue
            vistos = [a.capitulo for a in x.enlaces]
            if vistos != [str(n) for n in capitulos]:
                detalle = f"{nombre!r} enlaza a {vistos}, no a {capitulos}"
                hallazgos.append(Hallazgo(asercion="ficha", clase="maquetacion", detalle=detalle))
            rotos = [a.capitulo for a in x.enlaces if _enlace_roto(a.capitulo, a)]
            if rotos:
                detalle = f"{nombre!r} tiene enlaces que no resuelven: {rotos}"
                hallazgos.append(Hallazgo(asercion="ficha", clase="maquetacion", detalle=detalle))
    return hallazgos


def _portada_hallazgos(e: LecturaEsperada, dom: Dom) -> list[Hallazgo]:
    hallazgos: list[Hallazgo] = []
    for campo, esperado, pintado, dueno in (
        ("título", e.titulo, dom.portada.titulo, "planificador"),
        ("dedicatoria", e.dedicatoria, dom.portada.dedicatoria, "entrevistador"),
    ):
        if not _norma(esperado):
            detalle = f"la {campo} no está en la story bible (rol dueño: {dueno})"
            hallazgos.append(Hallazgo(asercion="portada", clase="datos", detalle=detalle))
        elif _norma(pintado) != _norma(esperado):
            detalle = f"la portada pinta {campo} {pintado!r}"
            hallazgos.append(Hallazgo(asercion="portada", clase="maquetacion", detalle=detalle))
    return hallazgos


def evaluar(e: LecturaEsperada, dom: Dom, errores_consola: list[str]) -> list[Hallazgo]:
    """Las aserciones de `ASERCIONES` sobre lo extraído. Vacía si la lectura es correcta."""
    if dom.estado != lectura.LISTA:
        detalle = f"la lectura está en data-estado={dom.estado!r}, no en {lectura.LISTA!r}"
        return [Hallazgo(asercion="estado", clase="maquetacion", detalle=detalle)]
    hallazgos: list[Hallazgo] = []

    def selector(detalle: str) -> None:
        hallazgos.append(Hallazgo(asercion="selectores", clase="maquetacion", detalle=detalle))

    raiz = dom.raiz or _Raiz()
    if (raiz.novel_id, raiz.version) != (e.novel_id, str(e.version)):
        selector(f"la raíz pinta la novela {raiz.novel_id!r} versión {raiz.version!r}")
    for testid, cuantos in cardinalidades(e).items():
        vistos = dom.cuentas.get(testid, 0)
        if vistos == 0 and cuantos > 0:
            selector(f"falta el selector {testid}")
        elif vistos != cuantos:
            selector(f"el selector {testid} aparece {vistos} veces, no {cuantos}")
    for testid in dom.fuera:
        selector(f"el selector {testid} está fuera de su contenedor")
    hallazgos += _indice(e, dom) + _ficha_hallazgos(e, dom) + _portada_hallazgos(e, dom)
    for mensaje in errores_consola:
        hallazgos.append(Hallazgo(asercion="consola", clase="maquetacion", detalle=mensaje))
    if dom.desbordes:
        detalle = f"desbordan: {', '.join(dom.desbordes)}"
        hallazgos.append(Hallazgo(asercion="desbordes", clase="maquetacion", detalle=detalle))
    return hallazgos


def lectura_esperada(con: sqlite3.Connection, *, novel_id: str, version: int) -> LecturaEsperada:
    fila = repository.leer_version(con, novel_id=novel_id, version=version)
    if fila is None:
        raise LookupError(f"la novela {novel_id} no tiene la versión {version}")
    portada = _portada.portada(con, novel_id=novel_id, version_fila=fila)
    ficha = _ficha.ficha(con, novel_id=novel_id, version=version)
    capitulos = repository.capitulos_de_version(con, novel_id=novel_id, version=version)
    return LecturaEsperada(
        novel_id=novel_id,
        version=version,
        titulo=portada.titulo,
        dedicatoria=portada.dedicatoria.texto,
        capitulos=[(c["numero"], c["titulo"], bool(c["modificado"])) for c in capitulos],
        personajes=[(p.nombre, list(p.capitulos)) for p in ficha.personajes],
        lugares=[(lugar.nombre, list(lugar.capitulos)) for lugar in ficha.lugares],
    )


# --- Extracción con el servidor MCP ----------------------------------------------------

# Los contenedores de cada selector, leídos de la columna «Dentro de» de CL-03.
_CONTENEDORES = {
    s.testid: re.findall(r"`([^`]+)`", s.dentro) for s in lectura.SELECTORES if s.dentro != "—"
}
_SELECTORES = {t: lectura.selector(t) for t in sorted(lectura.TESTIDS)}

_ESTADO_JS = (
    "() => { const r = document.querySelector(__RAIZ__);"
    " return r ? r.dataset.estado || null : null; }"
)

_EXTRAER_JS = """() => {
  const S = __S__, C = __C__;
  const q = (sel, raiz = document) => Array.from(raiz.querySelectorAll(sel));
  const uno = (sel, raiz = document) => raiz.querySelector(sel);
  const texto = (el) => (el ? el.textContent.trim() : null);
  const resuelve = (h) => !!(h && h.startsWith('#') && document.getElementById(h.slice(1)));
  const enlace = (el) => {
    const a = el.matches('a[href]') ? el : uno('a[href]', el);
    const href = a ? a.getAttribute('href') : null;
    return { href, resuelve: resuelve(href) };
  };
  const marca = (el) => !!uno(S['capitulo-modificado'], el);
  const raiz = uno(S['lectura']);
  const cuentas = {}, fuera = [], desbordes = [];
  for (const [t, sel] of Object.entries(S)) {
    const els = q(sel);
    cuentas[t] = els.length;
    const cs = C[t] || [];
    const dentro = (el) => cs.some((c) => el.parentElement && el.parentElement.closest(S[c]));
    if (cs.length && els.some((el) => !dentro(el))) fuera.push(t);
    const ancho = (el) => el.scrollWidth > el.clientWidth + 1
      && getComputedStyle(el).overflowX === 'visible' && el.clientWidth > 0;
    if (els.some(ancho)) desbordes.push(t);
  }
  const doc = document.documentElement;
  if (doc.scrollWidth > doc.clientWidth + 1) desbordes.push('documento');
  return {
    estado: raiz ? raiz.dataset.estado || null : null,
    raiz: raiz ? { novel_id: raiz.dataset.novelId || null,
                   version: raiz.dataset.version || null } : null,
    cuentas, fuera, desbordes,
    indice: q(S['indice-entrada']).map((el) => ({
      capitulo: el.dataset.capitulo || null, ...enlace(el), modificado: marca(el) })),
    capitulos: q(S['capitulo']).map((el) => ({
      capitulo: el.dataset.capitulo || null, id: el.id || null,
      titulo: texto(uno(S['capitulo-titulo'], el)), modificado: marca(el) })),
    ficha: ['ficha-personaje', 'ficha-lugar'].flatMap((t) => q(S[t]).map((el) => ({
      tipo: t, nombre: el.dataset.nombre || null,
      enlaces: q(S['ficha-enlace-capitulo'], el).map((a) => ({
        capitulo: a.dataset.capitulo || null, ...enlace(a) })) }))),
    portada: { titulo: texto(uno(S['portada-titulo'])),
               dedicatoria: texto(uno(S['portada-dedicatoria'])) },
  };
}"""


class ErrorServidorMCP(Exception):
    """El servidor MCP no respondió o respondió con un error."""


# Lo que significa «el servidor no está o no contesta»: el validador falla con el motivo, no
# revienta la generación. Cualquier otra excepción es un bug y se propaga.
_FALLOS_DEL_SERVIDOR = (OSError, httpx2.HTTPError, MCPError, ErrorServidorMCP, TimeoutError)


def _hoja(e: BaseException) -> BaseException:
    """La primera excepción real dentro de los grupos que levantan los task groups."""
    while isinstance(e, BaseExceptionGroup):
        e = e.exceptions[0]
    return e


def _texto(resultado: object) -> str:
    if getattr(resultado, "is_error", False):
        raise ErrorServidorMCP(" ".join(getattr(c, "text", "") for c in resultado.content))  # type: ignore[attr-defined]
    return "\n".join(getattr(c, "text", "") for c in getattr(resultado, "content", []))


def _resultado_json(texto: str) -> object:
    """El bloque `### Result` de `browser_evaluate`, que el servidor da como JSON."""
    cuerpo = texto.split("### Result", 1)[-1].split("\n### ", 1)[0].strip()
    return json.loads(cuerpo)


def _errores_consola(texto: str) -> list[str]:
    """Los errores de `browser_console_messages` con `level = error`. La cabecera —una o dos
    líneas— dice cuántos hay y termina en una línea en blanco; cada entrada empieza en una
    línea sin sangría (las siguientes son su pila). Una excepción no capturada sale sin
    prefijo, así que no se filtra por él (A-118)."""
    cuerpo = texto.split("### Result", 1)[-1].split("\n### ", 1)[0].strip()
    cuantos = re.search(r"Errors:\s*(\d+)", cuerpo)
    if cuantos is None or int(cuantos.group(1)) == 0:
        return []
    _, _, mensajes = cuerpo.partition("\n\n")
    entradas = [
        linea.strip()
        for linea in mensajes.splitlines()
        if linea.strip() and not linea[:1].isspace()
    ]
    if not entradas:
        return [f"{cuantos.group(1)} errores de consola"]
    return entradas


class RenderVisualMCP:
    """`render_visual` contra un servidor Playwright MCP, con llamadas guionizadas."""

    def __init__(
        self,
        config: Config,
        db: BaseDatos,
        *,
        mcp_url: str,
        lectura_url: str,
        espera_lista_segundos: float | None = None,
    ) -> None:
        umbrales = config.umbrales.render_visual
        self.db = db
        self.mcp_url = mcp_url
        self.lectura_url = lectura_url
        self.espera = (
            espera_lista_segundos
            if espera_lista_segundos is not None
            else umbrales.espera_lista_segundos
        )
        self.timeout = umbrales.timeout_llamada_segundos

    async def __call__(self, *, novel_id: str, version: int) -> VeredictoGate:
        esperado = await self.db.ejecutar(
            partial(lectura_esperada, novel_id=novel_id, version=version)
        )
        try:
            dom, consola = await self._extraer(lectura.url(self.lectura_url, novel_id, version))
        except Exception as e:
            causa = _hoja(e)
            if not isinstance(causa, _FALLOS_DEL_SERVIDOR):
                raise
            return VeredictoGate(
                nombre=NOMBRE,
                pasa=False,
                valor=0.0,
                detalle=f"el servidor Playwright MCP en {self.mcp_url} no respondió: "
                f"{type(causa).__name__}: {causa}",
            )
        hallazgos = evaluar(esperado, dom, consola)
        if hallazgos:
            return VeredictoGate(
                nombre=NOMBRE,
                pasa=False,
                valor=0.0,
                detalle="; ".join(h.texto() for h in hallazgos),
            )
        return VeredictoGate(
            nombre=NOMBRE,
            pasa=True,
            valor=1.0,
            detalle=f"la lectura de la versión {version} pasa: "
            + ", ".join(a.nombre for a in ASERCIONES),
        )

    async def _extraer(self, url: str) -> tuple[Dom, list[str]]:
        raiz = json.dumps(_SELECTORES["lectura"])
        extraer = _EXTRAER_JS.replace("__S__", json.dumps(_SELECTORES)).replace(
            "__C__", json.dumps(_CONTENEDORES)
        )
        async with (
            streamable_http_client(self.mcp_url) as flujos,
            ClientSession(flujos[0], flujos[1], read_timeout_seconds=self.timeout) as sesion,
        ):
            with anyio.fail_after(self.timeout):
                await sesion.initialize()
                _texto(await sesion.call_tool("browser_navigate", {"url": url}))
            try:
                estado = await self._esperar_estado(sesion, _ESTADO_JS.replace("__RAIZ__", raiz))
                if estado != lectura.LISTA:
                    return Dom(estado=estado), []
                with anyio.fail_after(self.timeout):
                    dom = Dom.model_validate(
                        _resultado_json(
                            _texto(
                                await sesion.call_tool("browser_evaluate", {"function": extraer})
                            )
                        )
                    )
                    consola = _errores_consola(
                        _texto(
                            await sesion.call_tool("browser_console_messages", {"level": "error"})
                        )
                    )
                return dom, consola
            finally:
                with anyio.move_on_after(self.timeout, shield=True):
                    await sesion.call_tool("browser_close", {})

    async def _esperar_estado(self, sesion: ClientSession, funcion: str) -> str | None:
        """CL-02: sondea `data-estado` hasta `lista` o `error`, o hasta agotar la espera."""
        estado: str | None = None
        with anyio.move_on_after(self.espera):
            while True:
                with anyio.fail_after(self.timeout):
                    valor = _resultado_json(
                        _texto(await sesion.call_tool("browser_evaluate", {"function": funcion}))
                    )
                estado = valor if isinstance(valor, str) else None
                if estado in (lectura.LISTA, lectura.ERROR):
                    return estado
                await anyio.sleep(0.25)
        return estado


def render_de_entorno(config: Config, db: BaseDatos) -> RenderVisual:
    """La implementación de producción: con el servidor MCP si el entorno lo configura."""
    mcp_url = os.environ.get("PLAYWRIGHT_MCP_URL", "").strip()
    lectura_url = os.environ.get("STORYMAKER_LECTURA_URL", "").strip()
    if mcp_url and lectura_url:
        return RenderVisualMCP(config, db, mcp_url=mcp_url, lectura_url=lectura_url)
    return SinNavegador()
