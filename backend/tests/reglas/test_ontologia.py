"""H2 · prueba 4 — A-23, RNF-07.

Comprobador sobre los `models.py`. Los nombres de las clases del codigo son los
de la ontologia, sin excepciones (AGENTS.md regla 1), y la lista no se escribe
aqui: se lee de `docs/definitions.md`, que es la fuente. Una lista copiada se
queda vieja el dia que la ontologia cambie, que es justo el dia en que esta
prueba tiene que fallar.

Cubre las dos direcciones. El punto ciego que `verification.md` anota en A-23 es
que detecta el nombre inventado pero no la clase que nadie implementa: la
segunda mitad de esta prueba lo cierra para la Capa 1.
"""

from __future__ import annotations

import ast
import re
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
REPOSITORIO = RAIZ.parent
DEFINICIONES = REPOSITORIO / "docs" / "definitions.md"

# Cada capa de la ontologia tiene su feature dueña (`architecture.md`
# § Anatomia de una feature). La tabla crece con cada hito.
MODELOS_POR_CAPA = {
    "Capa 1 — Obra": RAIZ / "app" / "novel" / "models.py",
    "Capa 2 — Canon y estado": RAIZ / "app" / "canon" / "models.py",
}

# Tres clases de la Capa 1 no llevan `models.py` y architecture.md lo dice:
# no son tablas de nadie.
SIN_TABLA_PROPIA = {"BibliaDeLaObra", "VentanaEfectiva"}


def _a_nombre_de_clase(titulo: str) -> str:
    """«Hilo de trama» -> HiloDeTrama. «Parte / Acto» -> Parte."""
    principal = titulo.split("/")[0]
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", principal) if unicodedata.category(c) != "Mn"
    )
    return "".join(palabra.capitalize() for palabra in re.findall(r"[A-Za-z]+", sin_tildes))


def _clases_de_la_capa(titulo: str) -> set[str]:
    texto = DEFINICIONES.read_text(encoding="utf-8")
    inicio = texto.index(f"## {titulo}")
    resto = texto[inicio + 1 :]
    fin = resto.index("\n## ") if "\n## " in resto else len(resto)
    seccion = resto[:fin]

    clases: set[str] = set()
    for linea in seccion.splitlines():
        if not linea.startswith("| "):
            continue
        celdas = [celda.strip() for celda in linea.strip("|").split("|")]
        if len(celdas) < 3 or celdas[0] in {"Clase", ""} or set(celdas[0]) <= {"-", " "}:
            continue
        clases.add(_a_nombre_de_clase(celdas[0]))
    return clases


def _clases_del_modulo(fichero: Path) -> set[str]:
    arbol = ast.parse(fichero.read_text(encoding="utf-8"), str(fichero))
    return {
        nodo.name
        for nodo in arbol.body
        if isinstance(nodo, ast.ClassDef) and not nodo.name.startswith("_")
    }


def test_los_nombres_de_las_clases_coinciden_con_la_ontologia() -> None:
    for capa, fichero in MODELOS_POR_CAPA.items():
        de_la_ontologia = _clases_de_la_capa(capa) - SIN_TABLA_PROPIA
        del_codigo = _clases_del_modulo(fichero)

        assert de_la_ontologia, f"no se han leido clases de «{capa}»"
        faltan = de_la_ontologia - del_codigo
        assert faltan == set(), f"{capa}: clases de la ontologia sin modelo: {sorted(faltan)}"


def test_ningun_modelo_inventa_una_clase_que_la_ontologia_no_tiene() -> None:
    # Tipos auxiliares que no son clases del dominio: enumerados de estado y
    # esquemas de escritura. Van con sufijo para que se distingan de un vistazo.
    auxiliares = re.compile(r"^(Estado|Tipo|Alcance|Nueva?|Nuevo)[A-Z]")

    for capa, fichero in MODELOS_POR_CAPA.items():
        de_la_ontologia = _clases_de_la_capa(capa)
        inventadas = {
            nombre
            for nombre in _clases_del_modulo(fichero)
            if nombre not in de_la_ontologia and not auxiliares.match(nombre)
        }
        assert inventadas == set(), (
            f"{capa}: nombres que no estan en la ontologia: {sorted(inventadas)}"
        )
