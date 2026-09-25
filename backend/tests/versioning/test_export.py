"""Export a PDF y `paridad_pdf_web` (P48, RF-EXP-01, RF-EXP-02, TO-003, TO-025, TO-045, D-22).

El PDF sale de `page.pdf()` de Playwright sobre la misma lectura que valida el gate, con medios
`print` (CL-04), **una vez por versión publicada**. `paridad_pdf_web` lo lee con `pypdf` y lo
compara con lo que la página pinta. Las comparaciones puras se prueban sin navegador; las que
generan el PDF necesitan el Chromium de Playwright (`uv run playwright install chromium`).
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader

from app.versioning import export
from app.versioning.paridad import CapituloWeb, LecturaWeb, PdfLeido, paridad
from tests.canon.test_hechos_por_version import publicada_con_uso
from tests.conftest import Instancia, ValidarContrato
from tests.dobles.guiones import guion_completo
from tests.fixtures.briefs import brief_ejemplo
from tests.fixtures.lectura.pagina import datos_de_version, pagina
from tests.fixtures.lectura.servidor import Paginas
from tests.process.test_orquestador import esperar

TOLERANCIA = 0.02

chromium = pytest.mark.skipif(
    not export.navegador_instalado(),
    reason="falta el Chromium de Playwright: uv run playwright install chromium (plan § 9)",
)


# --- Paridad pura ----------------------------------------------------------------------


def _web() -> LecturaWeb:
    return LecturaWeb(
        capitulos=[
            CapituloWeb(numero=1, titulo="Uno", palabras_texto=100, palabras_seccion=101),
            CapituloWeb(numero=2, titulo="Dos", palabras_texto=200, palabras_seccion=202),
        ],
        dedicatoria="Para Ondina, que siempre vuelve al puerto.",
        indice=["Uno", "Dos modificado"],
    )


def _pdf(**cambios: Any) -> PdfLeido:
    base: dict[str, Any] = {
        "paginas": [
            "El verano del Alondra\nPara Ondina, que siempre\nvuelve al puerto.\n"
            "1. Uno\n2. Dos\nmodificado",
            "Uno\n" + " ".join(["palabra"] * 100),
            "Dos\nmodificado\n" + " ".join(["palabra"] * 150),
            " ".join(["palabra"] * 50),
        ],
        "enlaces": ["capitulo-1", "capitulo-2"],
        "destinos": {"capitulo-1": 1, "capitulo-2": 2},
    }
    return PdfLeido.model_validate(base | cambios)


def _detalle(pdf: PdfLeido, web: LecturaWeb | None = None) -> str:
    v = paridad(web or _web(), pdf, TOLERANCIA)
    return "" if v.pasa else v.detalle


def test_un_pdf_fiel_pasa_la_paridad() -> None:
    v = paridad(_web(), _pdf(), TOLERANCIA)
    assert v.pasa and v.nombre == "paridad_pdf_web" and v.valor == 1.0, v.detalle


def test_falta_un_capitulo_o_su_titulo() -> None:
    paginas = _pdf().paginas
    sin_dos = _pdf(paginas=paginas[:2])
    assert "capítulo 2" in _detalle(sin_dos)
    cambiado = _pdf(paginas=[*paginas[:2], "Otro título\n" + paginas[2], paginas[3]])
    assert "capítulo 2" in _detalle(cambiado)


def test_falta_la_dedicatoria_o_el_indice() -> None:
    paginas = _pdf().paginas
    assert "dedicatoria" in _detalle(
        _pdf(paginas=["El verano del Alondra\n1. Uno\n2. Dos\nmodificado", *paginas[1:]])
    )
    assert "índice" in _detalle(
        _pdf(paginas=["El verano\nPara Ondina, que siempre vuelve al puerto.", *paginas[1:]])
    )


def test_el_recuento_de_palabras_fuera_de_tolerancia_falla() -> None:
    paginas = _pdf().paginas
    corto = _pdf(paginas=[*paginas[:3], " ".join(["palabra"] * 40)])
    detalle = _detalle(corto)
    assert "capítulo 2" in detalle and "palabras" in detalle
    # Dentro de tolerancia: 2 palabras de 200 es el 1 %.
    casi = _pdf(paginas=[*paginas[:3], " ".join(["palabra"] * 48)])
    assert _detalle(casi) == ""


def test_un_enlace_interno_que_no_resuelve_falla() -> None:
    roto = _pdf(enlaces=["capitulo-1", "capitulo-9"])
    assert "capitulo-9" in _detalle(roto)


# --- Con Playwright --------------------------------------------------------------------


def _servida(instancia: Instancia, paginas: Paginas, monkeypatch: pytest.MonkeyPatch) -> str:
    novela = publicada_con_uso(instancia)
    paginas.servir(novela, 1, pagina(datos_de_version(instancia.cliente, novela, 1)))
    monkeypatch.setenv("STORYMAKER_LECTURA_URL", paginas.base)
    return novela


@chromium
def test_export_una_vez_por_version_y_descarga(
    instancia: Instancia,
    paginas: Paginas,
    monkeypatch: pytest.MonkeyPatch,
    validar_contra_contrato: ValidarContrato,
) -> None:
    novela = _servida(instancia, paginas, monkeypatch)
    ruta = f"/novelas/{novela}/versiones/1/export"

    r = instancia.cliente.get(ruta)
    assert r.status_code == 404 and r.json()["type"] == "/problemas/export-no-disponible"
    validar_contra_contrato(r, "descargarExport")

    llamadas: list[str] = []
    original = export.renderizar

    async def contar(url: str, **kw: Any) -> Any:
        llamadas.append(url)
        return await original(url, **kw)

    monkeypatch.setattr(export, "renderizar", contar)
    r = instancia.cliente.post(ruta)
    validar_contra_contrato(r, "exportarVersion")
    assert r.status_code == 202 and r.json()["version"] == 1

    r = instancia.cliente.post(ruta)
    validar_contra_contrato(r, "exportarVersion")
    assert r.status_code == 200, r.json()
    cuerpo = r.json()
    assert cuerpo["estado"] == "disponible" and cuerpo["paridad_pdf_web"] is True
    assert cuerpo["url_descarga"] == ruta and cuerpo["generado_en"]
    assert len(llamadas) == 1

    r = instancia.cliente.get(ruta)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    assert [s.valor for s in instancia.trazas.scores_de("paridad_pdf_web")] == [1.0]

    # CL-04: con medios `print`, los controles no salen y todos los capítulos sí.
    texto = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
    assert "Pedir un cambio" not in texto
    for c in datos_de_version(instancia.cliente, novela, 1)["capitulos"]:
        assert c["titulo"] in texto


@chromium
def test_la_cli_exporta_una_version_publicada(
    instancia: Instancia,
    paginas: Paginas,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """D-22: `python -m app.versioning.export <novel_id> <version>`."""
    novela = _servida(instancia, paginas, monkeypatch)
    assert export.main([novela, "1"]) == 0
    salida = capsys.readouterr().out.strip().splitlines()[-1]
    assert Path(salida).is_file() and Path(salida).read_bytes().startswith(b"%PDF")
    # La segunda vez no lo rehace: devuelve el mismo fichero.
    assert export.main([novela, "1"]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1] == salida


def test_solo_se_exporta_una_version_publicada(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    """TO-045: una candidata o una rechazada responde 404 version-no-encontrada."""
    instancia.render.pasa = False
    guion_completo(instancia.modelo)
    novela = instancia.cliente.post("/novelas", json=brief_ejemplo()).json()["novel_id"]
    gid = instancia.cliente.post(f"/novelas/{novela}/generaciones").json()["generacion_id"]
    esperar(instancia.cliente, novela, gid, lambda g: g["es_terminal"])
    r = instancia.cliente.post(f"/novelas/{novela}/versiones/1/export")
    validar_contra_contrato(r, "exportarVersion")
    assert r.status_code == 404 and r.json()["type"] == "/problemas/version-no-encontrada"
    r = instancia.cliente.post(f"/novelas/{novela}/versiones/9/export")
    assert r.status_code == 404


def test_sin_url_de_lectura_el_export_falla_y_no_se_descarga(
    instancia: Instancia, validar_contra_contrato: ValidarContrato
) -> None:
    novela = publicada_con_uso(instancia)
    ruta = f"/novelas/{novela}/versiones/1/export"
    r = instancia.cliente.post(ruta)
    assert r.status_code == 202
    r = instancia.cliente.post(ruta)
    # Un export fallido se relanza en el siguiente POST (A-119).
    assert r.status_code == 202
    validar_contra_contrato(r, "exportarVersion")
    [fila] = instancia.app.state.recursos.db.ejecutar_sync(
        lambda con: con.execute(
            "SELECT estado, detalle FROM exportacion WHERE novel_id = ?", (novela,)
        ).fetchall()
    )
    assert fila["estado"] == "fallido" and "STORYMAKER_LECTURA_URL" in fila["detalle"]
    assert instancia.cliente.get(ruta).status_code == 404


def test_un_export_interrumpido_queda_fallido_al_arrancar(instancia: Instancia) -> None:
    novela = publicada_con_uso(instancia)
    db = instancia.app.state.recursos.db
    db.ejecutar_sync(
        lambda con: con.execute(
            "INSERT INTO exportacion (novel_id, version, estado, solicitado_en)"
            " VALUES (?, 1, 'en-curso', '2026-09-24T00:00:00Z')",
            (novela,),
        )
    )
    db.ejecutar_sync(export.sanear)
    [fila] = db.ejecutar_sync(
        lambda con: con.execute(
            "SELECT estado FROM exportacion WHERE novel_id = ?", (novela,)
        ).fetchall()
    )
    assert fila["estado"] == "fallido"
