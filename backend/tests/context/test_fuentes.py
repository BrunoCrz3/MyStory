"""Fuentes de las capas: recuperación por entidades, anticontexto y contador del proveedor
(RF-CTX-04, RNF-10)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.commons.config import cargar_config
from app.commons.db import conectar
from app.commons.db.migrar import aplicar_migraciones
from app.commons.llm import Mensaje, Peticion
from app.commons.llm.llamar import LlamadorModelo
from app.commons.llm.pool import PoolEnVuelo
from app.context.fuentes import ContadorProveedor, expresiones_repetidas, recuperar_fragmentos
from tests.arquitectura.comprobadores import RAIZ_REPO
from tests.dobles.modelo import ModeloGuionizado
from tests.dobles.trazador import RegistroTrazas

CONFIG = cargar_config(RAIZ_REPO / "config")


@pytest.fixture
def con(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    c = conectar(tmp_path / "fuentes.db")
    aplicar_migraciones(c)
    for n in ("n1", "n2"):
        c.execute(
            "INSERT INTO obra (novel_id, genero, tono, total_capitulos, creada_en)"
            " VALUES (?, 'g', 't', 10, '2026-01-01T00:00:00Z')",
            (n,),
        )
    yield c
    c.close()


def _aceptado(con: sqlite3.Connection, novel_id: str, numero: int, texto: str) -> None:
    con.execute(
        "INSERT INTO capitulo (id, novel_id, numero, version, estado, titulo, texto, aceptado_en)"
        " VALUES (?, ?, ?, 1, 'Aceptado', ?, ?, '2026-01-01T00:00:00Z')",
        (f"{novel_id}-{numero}", novel_id, numero, f"Capítulo {numero}", texto),
    )


def test_recuperado_filtra_por_entidades_antes_de_ordenar(con: sqlite3.Connection) -> None:
    _aceptado(con, "n1", 1, "El Alondra crujía en el puerto.\n\nUna gaviota graznó sobre el mar.")
    _aceptado(con, "n1", 2, "Ondina revisó las velas del Alondra.\n\nEl faro seguía apagado.")
    piezas = recuperar_fragmentos(
        con,
        novel_id="n1",
        version=1,
        entidades=["Alondra", "Ondina"],
        antes_de=3,
        excluir=set(),
        maximo=CONFIG.umbrales.recuperacion.max_fragmentos,
    )
    textos = [p.texto for p in piezas]
    # El párrafo de la gaviota se parece en tono, pero no nombra ninguna entidad del brief.
    assert all("gaviota" not in t and "faro" not in t for t in textos)
    assert textos[0] == "Ondina revisó las velas del Alondra."  # dos entidades, va primero
    assert "El Alondra crujía en el puerto." in textos


def test_recuperado_respeta_el_maximo_y_excluye_la_capa_local(con: sqlite3.Connection) -> None:
    for n in range(1, 6):
        _aceptado(con, "n1", n, f"El Alondra, capítulo {n}.")
    piezas = recuperar_fragmentos(
        con, novel_id="n1", version=1, entidades=["Alondra"], antes_de=6, excluir={5}, maximo=3
    )
    assert len(piezas) == 3
    assert all("capítulo 5" not in p.texto for p in piezas)


def test_recuperado_no_trae_nada_de_otra_novela(con: sqlite3.Connection) -> None:
    _aceptado(con, "n2", 1, "El Alondra de la otra novela.")
    assert (
        recuperar_fragmentos(
            con,
            novel_id="n1",
            version=1,
            entidades=["Alondra"],
            antes_de=5,
            excluir=set(),
            maximo=5,
        )
        == []
    )


def test_recuperado_normaliza_mayusculas_y_acentos(con: sqlite3.Connection) -> None:
    _aceptado(con, "n1", 1, "Llegaron a Cádiz de noche.")
    piezas = recuperar_fragmentos(
        con, novel_id="n1", version=1, entidades=["cadiz"], antes_de=2, excluir=set(), maximo=5
    )
    assert [p.texto for p in piezas] == ["Llegaron a Cádiz de noche."]


def test_expresiones_repetidas_en_la_ventana() -> None:
    n = CONFIG.umbrales.prosa.longitud_ngrama
    frase = " ".join(f"palabra{i}" for i in range(n))
    textos = [f"{frase} y más.", f"Otra vez {frase}.", "Nada que ver."]
    assert frase in expresiones_repetidas(textos, CONFIG)
    assert expresiones_repetidas(["una sola vez aquí dentro de nada"], CONFIG) == []


@pytest.mark.anyio
async def test_el_contador_de_produccion_usa_el_del_proveedor_y_cachea() -> None:
    modelo = ModeloGuionizado(CONFIG)
    llamador = LlamadorModelo(CONFIG, modelo, PoolEnVuelo(10**6), RegistroTrazas())
    contador = ContadorProveedor(llamador)
    a = await contador.contar_texto("redactor", "hola " * 40)
    b = await contador.contar_texto("redactor", "hola " * 40)
    assert a == b > 0
    assert len(modelo.recuentos) == 1
    p = Peticion(
        rol="redactor",
        system="s",
        mensajes=[Mensaje(role="user", contenido="x")],
        prompt="writer",
        hash_prompt="h",
    )
    assert await contador.contar_peticion(p) > 0
    assert sum(modelo.llamadas.values()) == 0  # contar no genera
