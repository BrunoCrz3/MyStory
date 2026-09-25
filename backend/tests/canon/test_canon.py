"""Story bible: consolidación, uso por capítulo y vigencia (RF-CANON-01…04, RD-05, D-06)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.canon.service import (
    Consolidacion,
    HechoNuevo,
    PromesaNueva,
    capitulos_que_usan,
    consolidar,
    hechos_vigentes,
    snapshot_de,
)
from app.commons.db import conectar, transaccion
from app.commons.db.migrar import aplicar_migraciones
from app.novel.service import crear_capitulo

TEXTO = (
    "Ondina soltó amarras al amanecer. El barco se llamaba Alondra y crujía como una casa vieja. "
    "En el puerto, su perro ladró hasta perderla de vista."
)


@pytest.fixture
def con(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    c = conectar(tmp_path / "canon.db")
    aplicar_migraciones(c)
    c.execute(
        "INSERT INTO obra (novel_id, genero, tono, total_capitulos, creada_en)"
        " VALUES ('n1', 'g', 't', 10, '2026-01-01T00:00:00Z'),"
        " ('n2', 'g', 't', 10, '2026-01-01T00:00:00Z')"
    )
    yield c
    c.close()


def _capitulo(con: sqlite3.Connection, numero: int, version: int = 1, novel_id: str = "n1") -> str:
    return crear_capitulo(con, novel_id=novel_id, numero=numero, version=version)


def _entrada(capitulo_id: str, numero: int, **extra: object) -> Consolidacion:
    base: dict[str, object] = {
        "capitulo_id": capitulo_id,
        "numero": numero,
        "hechos_nuevos": [
            HechoNuevo(
                enunciado="El barco se llama Alondra",
                tipo="objeto",
                fragmento_soporte="El barco se llamaba Alondra",
            ),
            HechoNuevo(
                enunciado="Ondina tiene un perro",
                tipo="relacion",
                fragmento_soporte="su perro ladró",
            ),
        ],
        "promesas_abiertas": [PromesaNueva(enunciado="¿Volverá a puerto?", tipo="pregunta")],
        "personajes_presentes": ["Ondina"],
        "ubicaciones": {"Ondina": "el puerto"},
        "momento": numero * 10,
    }
    base.update(extra)
    return Consolidacion.model_validate(base)


def _adoptar_todo(_: object) -> bool:
    return True


def test_consolidar_escribe_hechos_usos_promesas_y_snapshot(con: sqlite3.Connection) -> None:
    c1 = _capitulo(con, 1)
    with transaccion(con):
        resultado = consolidar(
            con,
            novel_id="n1",
            version=1,
            texto=TEXTO,
            entrada=_entrada(c1, 1),
            decidir=_adoptar_todo,
        )
    assert len(resultado.adoptados) == 2
    vigentes = hechos_vigentes(con, novel_id="n1", version=1)
    assert {h.enunciado for h in vigentes} == {"El barco se llama Alondra", "Ondina tiene un perro"}
    assert all(h.capitulos_usan == [1] and h.capitulo_establece == 1 for h in vigentes)
    snap = snapshot_de(con, novel_id="n1", version=1, capitulo_id=c1)
    assert snap is not None
    assert "El barco se llama Alondra" in snap.hechos
    assert snap.promesas_pendientes == ["¿Volverá a puerto?"]
    assert snap.personajes_presentes == ["Ondina"]


def test_si_algo_falla_a_medias_no_queda_nada(con: sqlite3.Connection) -> None:
    c1 = _capitulo(con, 1)

    def falla_en_el_segundo(h: object) -> bool:
        if getattr(h, "enunciado", "") == "Ondina tiene un perro":
            raise RuntimeError("se cae a mitad de consolidar")
        return True

    with pytest.raises(RuntimeError), transaccion(con):
        consolidar(
            con,
            novel_id="n1",
            version=1,
            texto=TEXTO,
            entrada=_entrada(c1, 1),
            decidir=falla_en_el_segundo,
        )
    for tabla in ("hecho", "hecho_capitulo", "promesa", "snapshot"):
        assert con.execute(f"SELECT count(*) FROM {tabla}").fetchone()[0] == 0, tabla


def test_consolidar_dos_veces_es_idempotente(con: sqlite3.Connection) -> None:
    c1 = _capitulo(con, 1)
    for _ in range(2):
        with transaccion(con):
            consolidar(
                con,
                novel_id="n1",
                version=1,
                texto=TEXTO,
                entrada=_entrada(c1, 1),
                decidir=_adoptar_todo,
            )
    assert con.execute("SELECT count(*) FROM hecho").fetchone()[0] == 2
    assert con.execute("SELECT count(*) FROM hecho_capitulo").fetchone()[0] == 2
    assert con.execute("SELECT count(*) FROM snapshot").fetchone()[0] == 1


def test_hecho_sin_fragmento_literal_no_se_consolida(con: sqlite3.Connection) -> None:
    c1 = _capitulo(con, 1)
    entrada = _entrada(
        c1,
        1,
        hechos_nuevos=[
            HechoNuevo(
                enunciado="El perro se llama Luna",
                tipo="nombre",
                fragmento_soporte="su perro Luna ladró",
            ),
        ],
    )
    with transaccion(con):
        resultado = consolidar(
            con, novel_id="n1", version=1, texto=TEXTO, entrada=entrada, decidir=_adoptar_todo
        )
    assert [h.enunciado for h in resultado.sin_fragmento] == ["El perro se llama Luna"]
    assert hechos_vigentes(con, novel_id="n1", version=1) == []


def test_un_hecho_descartado_no_es_vigente_en_ninguna_version(con: sqlite3.Connection) -> None:
    c1 = _capitulo(con, 1)
    with transaccion(con):
        consolidar(
            con,
            novel_id="n1",
            version=1,
            texto=TEXTO,
            entrada=_entrada(c1, 1),
            decidir=lambda h: getattr(h, "enunciado", "") != "Ondina tiene un perro",
        )
    assert [h.enunciado for h in hechos_vigentes(con, novel_id="n1", version=1)] == [
        "El barco se llama Alondra"
    ]


def test_los_usos_de_capitulos_posteriores(con: sqlite3.Connection) -> None:
    c1, c2 = _capitulo(con, 1), _capitulo(con, 2)
    with transaccion(con):
        r1 = consolidar(
            con,
            novel_id="n1",
            version=1,
            texto=TEXTO,
            entrada=_entrada(c1, 1),
            decidir=_adoptar_todo,
        )
    barco = next(h for h in r1.adoptados if "Alondra" in h.enunciado)
    with transaccion(con):
        consolidar(
            con,
            novel_id="n1",
            version=1,
            texto="Otra vez el Alondra.",
            entrada=_entrada(
                c2, 2, hechos_nuevos=[], hechos_usados=[barco.hecho_id], promesas_abiertas=[]
            ),
            decidir=_adoptar_todo,
        )
    assert capitulos_que_usan(con, novel_id="n1", version=1, hecho_id=barco.hecho_id) == [1, 2]


def test_vigencia_no_estatus_un_hecho_retconeado_sigue_en_su_version(
    con: sqlite3.Connection,
) -> None:
    c1 = _capitulo(con, 1)
    with transaccion(con):
        r = consolidar(
            con,
            novel_id="n1",
            version=1,
            texto=TEXTO,
            entrada=_entrada(c1, 1),
            decidir=_adoptar_todo,
        )
    perro = next(h for h in r.adoptados if "perro" in h.enunciado)
    # El retcon de la versión 3 cierra el uso y el hecho: primero el uso, por RD-05.
    with transaccion(con):
        con.execute(
            "UPDATE hecho_capitulo SET version_hasta = 3 WHERE hecho_id = ?", (perro.hecho_id,)
        )
        con.execute(
            "UPDATE hecho SET version_hasta = 3, estado = 'retconeado' WHERE id = ?",
            (perro.hecho_id,),
        )
    assert "Ondina tiene un perro" in {
        h.enunciado for h in hechos_vigentes(con, novel_id="n1", version=1)
    }
    assert "Ondina tiene un perro" not in {
        h.enunciado for h in hechos_vigentes(con, novel_id="n1", version=3)
    }


def test_rd05_un_uso_fuera_de_la_vigencia_de_su_hecho_se_rechaza(
    con: sqlite3.Connection,
) -> None:
    c1 = _capitulo(con, 1)
    with transaccion(con):
        r = consolidar(
            con,
            novel_id="n1",
            version=2,
            texto=TEXTO,
            entrada=_entrada(c1, 1),
            decidir=_adoptar_todo,
        )
    hecho = r.adoptados[0].hecho_id
    with pytest.raises(sqlite3.IntegrityError, match="RD-05"):
        con.execute(
            "INSERT INTO hecho_capitulo (novel_id, hecho_id, capitulo_id, version_desde)"
            " VALUES ('n1', ?, ?, 1)",
            (hecho, c1),
        )
    with pytest.raises(sqlite3.IntegrityError, match="RD-05"):
        con.execute("UPDATE hecho SET version_hasta = 3 WHERE id = ?", (hecho,))


def test_el_analisis_de_impacto_usa_el_indice(con: sqlite3.Connection) -> None:
    plan = " ".join(
        r[3]
        for r in con.execute(
            "EXPLAIN QUERY PLAN SELECT capitulo_id FROM hecho_capitulo WHERE novel_id = ? AND "
            "hecho_id = ? AND version_desde <= ? AND (version_hasta IS NULL OR ? < version_hasta)",
            ("n1", "h", 1, 1),
        )
    )
    assert "hecho_capitulo_por_hecho" in plan


def test_aislamiento_entre_novelas(con: sqlite3.Connection) -> None:
    c1 = _capitulo(con, 1, novel_id="n1")
    with transaccion(con):
        consolidar(
            con,
            novel_id="n1",
            version=1,
            texto=TEXTO,
            entrada=_entrada(c1, 1),
            decidir=_adoptar_todo,
        )
    assert hechos_vigentes(con, novel_id="n2", version=1) == []
