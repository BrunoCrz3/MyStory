"""Página `lectura` de prueba (P46, D-24): una versión publicada pintada como dice la spec § 4.4.

La generan las pruebas desde la API de lectura, con los selectores de `app/versioning/lectura.py`,
para que `render_visual` y el export se prueben contra un DOM que cumple el contrato sin
depender del frontend. Lleva su hoja `@media print` (CL-04): en pantalla los capítulos se
pliegan y hay controles; al imprimir, todos los capítulos se ven, cada uno en su página, y los
controles desaparecen.
"""

from __future__ import annotations

import html
from typing import Any

from fastapi.testclient import TestClient

from app.versioning.lectura import LISTA

ESTILO = """
body { font-family: Georgia, serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; }
.plegado .cuerpo { display: none; }
.control { border: 1px solid #999; padding: .25rem .5rem; }
[data-testid="capitulo-modificado"] { color: #a05; font-size: .8rem; }
@media print {
  .plegado .cuerpo { display: block; }
  [data-testid="capitulo"] { display: block; break-before: page; }
  .control { display: none; }
}
"""


def datos_de_version(cliente: TestClient, novela: str, version: int) -> dict[str, Any]:
    base = f"/novelas/{novela}/versiones/{version}"
    return {
        "novel_id": novela,
        "version": version,
        "portada": cliente.get(f"{base}/portada").json(),
        "capitulos": cliente.get(f"{base}/capitulos").json(),
        "ficha": cliente.get(f"{base}/ficha").json(),
    }


def _t(testid: str) -> str:
    return f'data-testid="{testid}"'


def _modificado(c: dict[str, Any]) -> str:
    return f"<span {_t('capitulo-modificado')}>modificado</span>" if c["modificado"] else ""


def _entrada_ficha(tipo: str, e: dict[str, Any]) -> str:
    enlaces = "".join(
        f'<a {_t("ficha-enlace-capitulo")} data-capitulo="{n}" href="#capitulo-{n}">{n}</a> '
        for n in e["capitulos"]
    )
    return (
        f'<li {_t(tipo)} data-nombre="{html.escape(e["nombre"])}">'
        f"{html.escape(e['nombre'])}: {enlaces}</li>"
    )


def pagina(datos: dict[str, Any], *, estado: str = LISTA, sin: tuple[str, ...] = ()) -> str:
    """El HTML de la lectura. `estado` cambia `data-estado`; `sin` quita elementos por
    `data-testid`, para que las pruebas del gate vean fallar un selector ausente."""
    p, capitulos, ficha = datos["portada"], datos["capitulos"], datos["ficha"]

    def si(testid: str, contenido: str) -> str:
        return "" if testid in sin else contenido

    indice = "".join(
        si(
            "indice-entrada",
            f'<li {_t("indice-entrada")} data-capitulo="{c["numero"]}">'
            f'<a href="#capitulo-{c["numero"]}">{html.escape(c["titulo"] or "")}</a>'
            f"{_modificado(c)}</li>",
        )
        for c in capitulos
    )
    cuerpo_capitulos = "".join(
        si(
            "capitulo",
            f'<section {_t("capitulo")} data-capitulo="{c["numero"]}" id="capitulo-{c["numero"]}"'
            f' class="plegado"><h2 {_t("capitulo-titulo")}>{html.escape(c["titulo"] or "")}</h2>'
            f"{_modificado(c)}"
            f'<div class="cuerpo"><div {_t("capitulo-texto")}>{html.escape(c["texto"] or "")}</div>'
            f"</div></section>",
        )
        for c in capitulos
    )
    personajes = "".join(_entrada_ficha("ficha-personaje", e) for e in ficha["personajes"])
    lugares = "".join(_entrada_ficha("ficha-lugar", e) for e in ficha["lugares"])
    return (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        f"<title>{html.escape(p['titulo'])}</title><style>{ESTILO}</style></head><body>"
        f'<main {_t("lectura")} data-estado="{estado}" data-novel-id="{datos["novel_id"]}"'
        f' data-version="{datos["version"]}">'
        + si(
            "portada",
            f"<header {_t('portada')}><h1 {_t('portada-titulo')}>{html.escape(p['titulo'])}</h1>"
            f"<p {_t('portada-dedicatoria')}>{html.escape(p['dedicatoria']['texto'])}</p></header>",
        )
        + '<nav class="control"><button type="button">Pedir un cambio</button></nav>'
        + si("indice", f"<ol {_t('indice')}>{indice}</ol>")
        + si("ficha", f"<ul {_t('ficha')}>{personajes}{lugares}</ul>")
        + cuerpo_capitulos
        + "</main></body></html>"
    )
