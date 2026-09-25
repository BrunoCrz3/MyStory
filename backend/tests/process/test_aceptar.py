"""Aceptación y extracción: el único punto donde la story bible cambia
(RF-PROC-10, RF-CANON-01, RF-CANON-04, D-07)."""

from __future__ import annotations

from typing import Any

import pytest

from app.commons.errores import TransicionInvalida
from app.process.aceptar import aceptar
from app.process.capitulo import ciclo_capitulo
from tests.conftest import Entorno
from tests.fixtures.borradores import borrador
from tests.fixtures.briefs import brief_ejemplo
from tests.fixtures.extracciones import extraccion
from tests.fixtures.planificada import novela_planificada

OBLIGATORIO = next(
    e["enunciado"] for e in brief_ejemplo()["elementos_personalizados"] if e["obligatorio"]
)


def _encolar_extraccion(entorno: Entorno, **kw: Any) -> None:
    def responder(peticion: Any) -> dict[str, Any]:
        texto = peticion.mensajes[0].contenido.split('<capa nombre="local">', 1)[1]
        texto = texto.split("</capa>", 1)[0]
        cuerpo = [ln for ln in texto.splitlines() if ln.strip() and not ln.endswith(":")]
        return extraccion(cuerpo[0], **kw)

    entorno.modelo.encolar("extractor", responder)


async def _capitulo_aceptado(entorno: Entorno, novela: str, numero: int = 1, **kw: Any) -> str:
    entorno.modelo.encolar("redactor", borrador(titulo=f"Capítulo {numero} aceptado"))
    resultado = await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=numero)
    _encolar_extraccion(entorno, **kw)
    await aceptar(entorno.recursos, novel_id=novela, version=1, numero=numero, resultado=resultado)
    return resultado.capitulo_id


@pytest.mark.anyio
async def test_aceptar_consolida_texto_canon_resumen_y_elementos(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    cid = await _capitulo_aceptado(entorno, novela, elementos=[OBLIGATORIO])
    (cap,) = entorno.consultar(
        "SELECT estado, titulo, palabras, gancho_cierre, texto, aceptado_en"
        " FROM capitulo WHERE id = ?",
        cid,
    )
    assert cap["estado"] == "Aceptado"
    assert cap["titulo"] == "Capítulo 1 aceptado"
    assert cap["palabras"] == 1200
    assert cap["gancho_cierre"] == "El barco la espera."
    hechos = entorno.consultar(
        "SELECT estado, fragmento_soporte FROM hecho WHERE novel_id = ?", novela
    )
    assert [h["estado"] for h in hechos] == ["adoptado"]
    assert hechos[0]["fragmento_soporte"] in cap["texto"]
    assert (
        entorno.consultar("SELECT texto FROM resumen_capitulo WHERE capitulo_id = ?", cid)[0][
            "texto"
        ]
        == "Ondina mira el mar y decide volver."
    )
    assert len(entorno.consultar("SELECT 1 FROM snapshot WHERE capitulo_id = ?", cid)) == 1
    assert len(entorno.consultar("SELECT 1 FROM elemento_capitulo WHERE capitulo_id = ?", cid)) == 1
    assert len(entorno.consultar("SELECT 1 FROM evento_capitulo WHERE capitulo_id = ?", cid)) == 1


@pytest.mark.anyio
async def test_el_extractor_corre_despues_de_aceptar_y_nunca_antes(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    await _capitulo_aceptado(entorno, novela)
    generaciones = entorno.trazas.nombres("generacion")
    assert generaciones[-3:] == ["writer", "judge", "extractor"]
    spans = entorno.trazas.nombres("span")
    assert spans.index("hook_capitulo") < spans.index("consolidar")


@pytest.mark.anyio
async def test_un_borrador_rechazado_no_deja_rastro(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    rechazado = borrador(500, extra="Rechazado: nadie debe leer esta frase.")
    entorno.modelo.encolar("redactor", rechazado, borrador())
    resultado = await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=1)
    _encolar_extraccion(entorno)
    await aceptar(entorno.recursos, novel_id=novela, version=1, numero=1, resultado=resultado)
    assert entorno.modelo.llamadas["extractor"] == 1
    for tabla, columna in [
        ("capitulo", "texto"),
        ("hecho", "fragmento_soporte"),
        ("resumen_capitulo", "texto"),
        ("snapshot", "contenido"),
    ]:
        filas = entorno.consultar(f"SELECT {columna} AS c FROM {tabla} WHERE novel_id = ?", novela)
        assert all("Rechazado" not in (f["c"] or "") for f in filas), tabla


@pytest.mark.anyio
async def test_los_hechos_entran_propuestos_y_el_policy_decide(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    await _capitulo_aceptado(entorno, novela)
    decisiones = entorno.consultar(
        "SELECT sujeto, regla, resultado FROM audit_log WHERE novel_id = ? AND sujeto = 'hecho'",
        novela,
    )
    assert [(d["regla"], d["resultado"]) for d in decisiones] == [
        ("fragmento-literal-y-nuevo", "adoptar")
    ]


@pytest.mark.anyio
async def test_el_capitulo_siguiente_usa_los_hechos_por_su_alias(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    await _capitulo_aceptado(entorno, novela, numero=1, promesas=["¿Volverá a puerto?"])
    await _capitulo_aceptado(entorno, novela, numero=2, usados=["H1"], pagadas=["P1"])
    usos = entorno.consultar(
        "SELECT c.numero FROM hecho_capitulo u JOIN capitulo c ON c.id = u.capitulo_id"
        " WHERE u.novel_id = ? ORDER BY c.numero",
        novela,
    )
    # El hecho del 2 repite el del 1 y se descarta por duplicado: el 2 solo usa H1.
    assert [u["numero"] for u in usos] == [1, 2]
    extractor = [p for p in entorno.modelo.peticiones if p.rol == "extractor"][-1]
    assert "H1" in extractor.mensajes[0].contenido
    # El estado se deriva de las filas (TO-047): el 2 queda vinculado como pago.
    vinculos = entorno.consultar(
        "SELECT c.numero, v.papel FROM promesa_capitulo v JOIN capitulo c ON c.id = v.capitulo_id"
        " WHERE v.novel_id = ? ORDER BY c.numero",
        novela,
    )
    assert [(v["numero"], v["papel"]) for v in vinculos] == [(1, "apertura"), (2, "pago")]


@pytest.mark.anyio
async def test_aceptar_dos_veces_no_duplica(entorno: Entorno) -> None:
    novela = await novela_planificada(entorno)
    entorno.modelo.encolar("redactor", borrador())
    resultado = await ciclo_capitulo(entorno.recursos, novel_id=novela, version=1, numero=1)
    _encolar_extraccion(entorno)
    await aceptar(entorno.recursos, novel_id=novela, version=1, numero=1, resultado=resultado)
    antes = entorno.consultar("SELECT count(*) AS n FROM hecho")[0]["n"]
    _encolar_extraccion(entorno)
    with pytest.raises(TransicionInvalida):
        await aceptar(entorno.recursos, novel_id=novela, version=1, numero=1, resultado=resultado)
    assert entorno.consultar("SELECT count(*) AS n FROM hecho")[0]["n"] == antes


@pytest.mark.anyio
async def test_muchos_hechos_conocidos_no_impiden_extraer(entorno: Entorno) -> None:
    # Humo real del P44: tras una regeneración, la lista de hechos conocidos del extractor
    # pasaba de 4.000 tokens en la capa Estructural, que no se degrada, y la novela se detenía
    # con ContextoNoCabe. Los hechos conocidos son estado del mundo: van en la capa Estado.
    import uuid

    novela = await novela_planificada(entorno)
    relleno = "un detalle más de la historia que el lector ya conoce y que nadie discute"
    entorno.recursos.db.en_transaccion_sync(
        lambda con: con.executemany(
            "INSERT INTO hecho (id, novel_id, enunciado, tipo, estado, origen, version_desde,"
            " creado_en) VALUES (?, ?, ?, 'suceso', 'adoptado', 'brief', 1, '2026-01-01')",
            [(str(uuid.uuid4()), novela, f"Hecho {i}: {relleno}") for i in range(250)],
        )
    )
    cid = await _capitulo_aceptado(entorno, novela)
    assert entorno.consultar("SELECT estado FROM capitulo WHERE id = ?", cid)[0]["estado"] == (
        "Aceptado"
    )
    [peticion] = [p for p in entorno.modelo.peticiones if p.rol == "extractor"]
    estado = peticion.mensajes[0].contenido.split('<capa nombre="estado">', 1)[1]
    assert "Hechos ya conocidos" in estado.split("</capa>", 1)[0]
