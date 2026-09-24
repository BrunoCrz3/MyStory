"""Contrato de lectura como dato (spec § 4.4, CL-01…CL-05, TO-037).

La página `lectura` del frontend es el segundo contrato entre backend y frontend: no es HTTP
sino DOM. Aquí está entero —la ruta, los estados de carga y la tabla de selectores de CL-03—
como **un único dato**, que usan `render_visual` y `paridad_pdf_web`. Ningún otro módulo de
`app/` escribe un selector (lo comprueba una prueba de arquitectura), y la tabla es la de la
spec, leída del fichero por otra prueba: cambiar una sin la otra rompe la suite.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

# CL-01: la versión entera, en un solo documento, sobre `STORYMAKER_LECTURA_URL`.
RUTA = "/novelas/{novel_id}/versiones/{version}"
# CL-02: el atributo `data-estado` de la raíz. Se espera a `lista`; `error` falla el gate.
ESTADOS = ("cargando", "lista", "error")
LISTA, ERROR = "lista", "error"


class Selector(BaseModel):
    """Una fila de CL-03, con el texto de sus columnas tal como lo dice la spec."""

    model_config = ConfigDict(frozen=True)

    testid: str
    cuantos: str
    dentro: str
    contenido: str


def _s(testid: str, cuantos: str, dentro: str, contenido: str) -> Selector:
    return Selector(testid=testid, cuantos=cuantos, dentro=dentro, contenido=contenido)


SELECTORES: tuple[Selector, ...] = (
    _s("lectura", "1", "—", "`data-estado`, `data-novel-id`, `data-version`"),
    _s("portada", "1", "`lectura`", "—"),
    _s("portada-titulo", "1", "`portada`", "Texto: `Portada.titulo`"),
    _s("portada-dedicatoria", "1", "`portada`", "Texto: `Dedicatoria.texto`"),
    _s("indice", "1", "`lectura`", "—"),
    _s(
        "indice-entrada",
        "Uno por capítulo, en orden",
        "`indice`",
        "`data-capitulo`; contiene un enlace a `#capitulo-{n}`",
    ),
    _s("ficha", "1", "`lectura`", "—"),
    _s("ficha-personaje", "Uno por entrada de `Ficha.personajes`", "`ficha`", "`data-nombre`"),
    _s("ficha-lugar", "Uno por entrada de `Ficha.lugares`", "`ficha`", "`data-nombre`"),
    _s(
        "ficha-enlace-capitulo",
        "Uno por capítulo de cada entrada",
        "`ficha-personaje` o `ficha-lugar`",
        "`data-capitulo`; enlace a `#capitulo-{n}`",
    ),
    _s(
        "capitulo",
        "Uno por capítulo, en orden",
        "`lectura`",
        '`data-capitulo`, `id="capitulo-{n}"`',
    ),
    _s("capitulo-titulo", "1 por capítulo", "`capitulo`", "Texto: `Capitulo.titulo`"),
    _s(
        "capitulo-texto",
        "1 por capítulo",
        "`capitulo`",
        "Texto: `Capitulo.texto`, sin añadidos, porque sobre él se cuentan las palabras de "
        "`paridad_pdf_web`",
    ),
    _s(
        "capitulo-modificado",
        "0 o 1",
        "`indice-entrada` y `capitulo`",
        "Presente **solo** si `modificado` es `true`",
    ),
)

TESTIDS = frozenset(s.testid for s in SELECTORES)


def url(base: str, novel_id: str, version: int) -> str:
    return base.rstrip("/") + RUTA.format(novel_id=novel_id, version=version)


def selector(testid: str, **atributos: str | int) -> str:
    """El selector CSS de un `data-testid` del contrato, con atributos `data-*` opcionales."""
    if testid not in TESTIDS:
        raise KeyError(f"{testid!r} no está en el contrato de lectura (CL-03)")
    extra = "".join(f'[data-{k.replace("_", "-")}="{v}"]' for k, v in atributos.items())
    return f'[data-testid="{testid}"]{extra}'
