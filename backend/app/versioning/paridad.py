"""`paridad_pdf_web`: el PDF exportado dice lo mismo que la lectura web (RF-EXP-02, O-16, A-103).

Compara el PDF, leído con `pypdf`, con lo que la página pinta con medios `print`, leído del DOM
en el mismo render del que sale el PDF. Comprueba el recuento y los títulos de capítulos, la
dedicatoria y el índice antes del primer capítulo, el recuento de palabras de cada capítulo
dentro de `export.tolerancia_recuento_palabras` y que cada enlace interno resuelve a una
página. `pypdf` solo **lee**: el PDF sale de Playwright, y así no se valida uno y se entrega
otro.

Cada capítulo empieza en su página (CL-04, `break-before: page`), así que un capítulo son las
páginas desde la que empieza por su título hasta la siguiente. A sus palabras se le restan las
que la sección pinta fuera de `capitulo-texto` —título, marca de modificado—, que la web cuenta
aparte.
"""

from __future__ import annotations

import io

from pydantic import BaseModel
from pypdf import PdfReader
from pypdf.generic import ArrayObject

from app.process.service import VeredictoGate

NOMBRE = "paridad_pdf_web"


class CapituloWeb(BaseModel):
    numero: int
    titulo: str
    palabras_texto: int
    palabras_seccion: int


class LecturaWeb(BaseModel):
    """Lo que la página pinta con medios `print`, leído del DOM."""

    capitulos: list[CapituloWeb]
    dedicatoria: str
    indice: list[str]


class PdfLeido(BaseModel):
    paginas: list[str]
    enlaces: list[str]
    # Destino con nombre → página (índice desde 0); -1 si no resuelve.
    destinos: dict[str, int]


def _norma(texto: str) -> str:
    return " ".join(texto.split())


def _palabras(texto: str) -> int:
    return len(texto.split())


def leer_pdf(datos: bytes) -> PdfLeido:
    lector = PdfReader(io.BytesIO(datos))
    destinos: dict[str, int] = {}
    for nombre, destino in (lector.named_destinations or {}).items():
        try:
            pagina = lector.get_destination_page_number(destino)
        except (KeyError, ValueError, AttributeError):
            pagina = None
        destinos[str(nombre).lstrip("/")] = -1 if pagina is None else pagina
    enlaces: list[str] = []
    for hoja in lector.pages:
        for anotacion in hoja.get("/Annots", []) or []:
            objeto = anotacion.get_object()
            if objeto.get("/Subtype") != "/Link":
                continue
            destino = objeto.get("/Dest")
            if destino is None or isinstance(destino, ArrayObject):
                # Un destino explícito apunta ya a una página; los externos no son de aquí.
                continue
            enlaces.append(str(destino).lstrip("/"))
    return PdfLeido(
        paginas=[p.extract_text() or "" for p in lector.pages],
        enlaces=enlaces,
        destinos=destinos,
    )


def _comienzos(web: LecturaWeb, pdf: PdfLeido, hallazgos: list[str]) -> list[int]:
    """La página donde empieza cada capítulo, en orden; -1 si no se encuentra."""
    comienzos: list[int] = []
    desde = 0
    for c in web.capitulos:
        titulo = _norma(c.titulo)
        pagina = next(
            (
                i
                for i in range(desde, len(pdf.paginas))
                if titulo and _norma(pdf.paginas[i]).startswith(titulo)
            ),
            -1,
        )
        if pagina < 0:
            hallazgos.append(f"falta el capítulo {c.numero} «{c.titulo}» en el PDF")
        else:
            desde = pagina + 1
        comienzos.append(pagina)
    return comienzos


def paridad(web: LecturaWeb, pdf: PdfLeido, tolerancia: float) -> VeredictoGate:
    hallazgos: list[str] = []
    comienzos = _comienzos(web, pdf, hallazgos)
    encontrados = [p for p in comienzos if p >= 0]
    primera = min(encontrados) if encontrados else len(pdf.paginas)
    preliminares = _norma(" ".join(pdf.paginas[:primera]))

    if _norma(web.dedicatoria) not in preliminares:
        hallazgos.append("la dedicatoria no está antes del primer capítulo del PDF")
    ausentes = [e for e in web.indice if _norma(e) not in preliminares]
    if len(web.indice) != len(web.capitulos) or ausentes:
        hallazgos.append(f"el índice del PDF no lista {ausentes or 'todos los capítulos'}")

    for k, (c, inicio) in enumerate(zip(web.capitulos, comienzos, strict=True)):
        if inicio < 0:
            continue
        siguientes = [p for p in comienzos[k + 1 :] if p >= 0]
        fin = siguientes[0] if siguientes else len(pdf.paginas)
        en_pdf = _palabras(" ".join(pdf.paginas[inicio:fin]))
        en_pdf -= c.palabras_seccion - c.palabras_texto
        if abs(en_pdf - c.palabras_texto) > tolerancia * max(c.palabras_texto, 1):
            hallazgos.append(
                f"el capítulo {c.numero} tiene {en_pdf} palabras en el PDF y "
                f"{c.palabras_texto} en la web (tolerancia {tolerancia:.0%})"
            )

    rotos = sorted({e for e in pdf.enlaces if pdf.destinos.get(e, -1) < 0})
    if rotos:
        hallazgos.append(f"enlaces internos que no resuelven: {', '.join(rotos)}")

    if hallazgos:
        return VeredictoGate(nombre=NOMBRE, pasa=False, valor=0.0, detalle="; ".join(hallazgos))
    return VeredictoGate(
        nombre=NOMBRE,
        pasa=True,
        valor=1.0,
        detalle=f"{len(web.capitulos)} capítulos, títulos, dedicatoria, índice, palabras y "
        f"{len(pdf.enlaces)} enlaces internos coinciden",
    )
