"""Contrato de lectura como dato (spec § 4.4, CL-01…CL-05, TO-037).

`versioning/lectura.py` es el único sitio de `app/` que conoce la ruta, los estados de carga y
los selectores de la página `lectura`. Estas pruebas lo atan a la tabla CL-03 de la spec,
leída del fichero, y comprueban que la página de prueba cumple el contrato.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

from app.versioning import lectura
from tests.arquitectura.comprobadores import RAIZ_REPO
from tests.canon.test_hechos_por_version import publicada_con_uso
from tests.conftest import Instancia
from tests.fixtures.lectura.pagina import datos_de_version, pagina

SPEC = RAIZ_REPO / "specs" / "spec1.md"


def _tabla_cl03() -> list[tuple[str, str, str, str]]:
    lineas = SPEC.read_text(encoding="utf-8").splitlines()
    inicio = next(i for i, x in enumerate(lineas) if x.startswith("| `data-testid` |")) + 2
    filas = []
    for linea in lineas[inicio:]:
        if not linea.startswith("|"):
            break
        celdas = [c.strip() for c in linea.strip("|").split("|")]
        filas.append((celdas[0].strip("`"), celdas[1], celdas[2], celdas[3]))
    return filas


def test_la_tabla_de_selectores_es_la_de_la_spec() -> None:
    assert [(s.testid, s.cuantos, s.dentro, s.contenido) for s in lectura.SELECTORES] == (
        _tabla_cl03()
    )


def test_ruta_estados_y_selector() -> None:
    assert lectura.ESTADOS == ("cargando", "lista", "error")
    assert lectura.url("http://127.0.0.1:5173/", "abc", 2) == (
        "http://127.0.0.1:5173/novelas/abc/versiones/2"
    )
    assert lectura.selector("capitulo-texto") == '[data-testid="capitulo-texto"]'
    assert lectura.selector("capitulo", capitulo=3) == '[data-testid="capitulo"][data-capitulo="3"]'


class _Arbol(HTMLParser):
    """Cada elemento con `data-testid`, con sus atributos y los `data-testid` que lo rodean."""

    VACIOS = frozenset({"meta", "link", "br", "img", "input", "hr"})

    def __init__(self) -> None:
        super().__init__()
        self.pila: list[dict[str, str | None]] = []
        self.elementos: list[tuple[dict[str, str | None], list[str]]] = []
        self.css = ""
        self._en_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        atributos = dict(attrs)
        if "data-testid" in atributos:
            ancestros = [a["data-testid"] or "" for a in self.pila if "data-testid" in a]
            self.elementos.append((atributos, ancestros))
        self._en_style = tag == "style"
        if tag not in self.VACIOS:
            self.pila.append(atributos)

    def handle_endtag(self, tag: str) -> None:
        self._en_style = False
        if tag not in self.VACIOS and self.pila:
            self.pila.pop()

    def handle_data(self, data: str) -> None:
        if self._en_style:
            self.css += data


def test_la_pagina_de_prueba_cumple_el_contrato(instancia: Instancia) -> None:
    novela = publicada_con_uso(instancia)
    datos = datos_de_version(instancia.cliente, novela, 1)
    html = pagina(datos)
    arbol = _Arbol()
    arbol.feed(html)

    def todos(testid: str) -> list[tuple[dict[str, str | None], list[str]]]:
        return [(a, anc) for a, anc in arbol.elementos if a["data-testid"] == testid]

    # CL-01 y CL-02: un solo documento, con la raíz lista y la versión.
    [(raiz, _)] = todos("lectura")
    assert raiz["data-estado"] == "lista" and raiz["data-version"] == "1"
    assert raiz["data-novel-id"] == novela

    # CL-03: cada selector con su cardinalidad y dentro de su contenedor.
    capitulos = datos["capitulos"]
    n = len(capitulos)
    esperado = {
        "portada": 1, "portada-titulo": 1, "portada-dedicatoria": 1, "indice": 1,
        "indice-entrada": n, "ficha": 1, "capitulo": n, "capitulo-titulo": n, "capitulo-texto": n,
        "ficha-personaje": len(datos["ficha"]["personajes"]),
        "ficha-lugar": len(datos["ficha"]["lugares"]),
    }  # fmt: skip
    for testid, cuantos in esperado.items():
        assert len(todos(testid)) == cuantos, testid
    for s in lectura.SELECTORES:
        contenedores = [c.strip("`") for c in re.findall(r"`[^`]+`", s.dentro)]
        for _, ancestros in todos(s.testid):
            assert not contenedores or any(c in ancestros for c in contenedores), s.testid
    assert [a["data-capitulo"] for a, _ in todos("capitulo")] == [
        str(c["numero"]) for c in capitulos
    ]
    assert all(a["id"] == f"capitulo-{a['data-capitulo']}" for a, _ in todos("capitulo"))
    enlaces = sum(
        len(p["capitulos"]) for p in datos["ficha"]["personajes"] + datos["ficha"]["lugares"]
    )
    assert len(todos("ficha-enlace-capitulo")) == enlaces
    modificados = [c["numero"] for c in capitulos if c["modificado"]]
    assert len(todos("capitulo-modificado")) == 2 * len(modificados)

    # CL-04: hoja de impresión con los capítulos visibles y los controles fuera.
    impresion = arbol.css.split("@media print", 1)[1]
    assert "display: block" in impresion and "break-before: page" in impresion
    assert ".control" in impresion and "display: none" in impresion
