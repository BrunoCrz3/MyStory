"""Export a PDF de una versión publicada (RF-EXP-01, RF-EXP-02, TO-003, TO-025, TO-045, D-22).

El PDF sale de `page.pdf()` de Playwright sobre **la misma lectura** que el gate valida con
`render_visual` (`STORYMAKER_LECTURA_URL` + CL-01): se espera a `data-estado = lista`, se emulan
los medios `print` (CL-04) y, del mismo render, se leen el DOM para `paridad_pdf_web` y el PDF.
Se genera **una vez por versión**: una fila `disponible` no se rehace. Solo una versión
`publicada` se exporta; una candidata o una rechazada es `version-no-encontrada`.

`python -m app.versioning.export <novel_id> <version>` hace lo mismo desde la línea de
comandos (D-22) e imprime la ruta del PDF.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import anyio
from playwright.async_api import Error as ErrorPlaywright
from playwright.async_api import async_playwright

from app.commons.config import cargar_config
from app.commons.db import BaseDatos, ruta_db
from app.commons.db.migrar import aplicar_migraciones
from app.commons.errores import ExportNoDisponible, NovelaNoEncontrada, VersionNoEncontrada
from app.commons.observabilidad import Trazador
from app.commons.observabilidad.langfuse import TrazadorLangfuse
from app.commons.recursos import Recursos
from app.commons.tiempo import ahora
from app.novel import service as novel
from app.versioning import lectura, paridad, repository
from app.versioning.schemas import Exportacion

_SELECTORES = {t: lectura.selector(t) for t in sorted(lectura.TESTIDS)}

_LISTA_O_ERROR_JS = (
    "(raiz) => { const r = document.querySelector(raiz);"
    " return !!r && ['lista', 'error'].includes(r.dataset.estado); }"
)
_ESTADO_JS = "(raiz) => document.querySelector(raiz).dataset.estado"

# Con medios `print` ya emulados: `innerText` respeta lo que se imprime.
_WEB_JS = """(S) => {
  const q = (sel, raiz = document) => Array.from(raiz.querySelectorAll(sel));
  const uno = (sel, raiz = document) => raiz.querySelector(sel);
  const palabras = (el) => (el ? el.innerText.split(/\\s+/).filter(Boolean).length : 0);
  const texto = (el) => (el ? el.innerText.trim() : '');
  return {
    capitulos: q(S['capitulo']).map((el) => ({
      numero: Number(el.dataset.capitulo),
      titulo: texto(uno(S['capitulo-titulo'], el)),
      palabras_texto: palabras(uno(S['capitulo-texto'], el)),
      palabras_seccion: palabras(el),
    })),
    dedicatoria: texto(uno(S['portada-dedicatoria'])),
    indice: q(S['indice-entrada']).map(texto),
  };
}"""


class ExportFallido(Exception):
    """El PDF no se pudo generar: sin lectura, sin navegador o la página no llegó a `lista`."""


def navegador_instalado() -> bool:
    """Si el Chromium de Playwright está en la máquina (`playwright install chromium`)."""

    async def comprobar() -> bool:
        async with async_playwright() as p:
            return Path(p.chromium.executable_path).is_file()

    try:
        return anyio.run(comprobar)
    except ErrorPlaywright:
        return False


async def renderizar(url: str, *, timeout_s: float) -> tuple[bytes, paridad.LecturaWeb]:
    """El PDF y lo que la página pinta con medios `print`, del mismo render."""
    ms = timeout_s * 1000
    raiz = _SELECTORES["lectura"]
    try:
        async with async_playwright() as p:
            navegador = await p.chromium.launch()
            try:
                pagina = await navegador.new_page()
                await pagina.goto(url, timeout=ms)
                await pagina.wait_for_function(_LISTA_O_ERROR_JS, arg=raiz, timeout=ms)
                estado = await pagina.evaluate(_ESTADO_JS, raiz)
                if estado != lectura.LISTA:
                    raise ExportFallido(f"la lectura está en data-estado={estado!r}")
                await pagina.emulate_media(media="print")
                web = paridad.LecturaWeb.model_validate(await pagina.evaluate(_WEB_JS, _SELECTORES))
                with anyio.fail_after(timeout_s):
                    pdf = await pagina.pdf(format="A4", print_background=True)
            finally:
                await navegador.close()
    except (ErrorPlaywright, TimeoutError) as e:
        raise ExportFallido(f"{type(e).__name__}: {str(e).splitlines()[0]}") from e
    return pdf, web


# --- Servicio --------------------------------------------------------------------------


def _vista(fila: dict[str, Any]) -> Exportacion:
    disponible = fila["estado"] == "disponible"
    return Exportacion(
        version=fila["version"],
        estado=fila["estado"],
        url_descarga=(
            f"/novelas/{fila['novel_id']}/versiones/{fila['version']}/export"
            if disponible
            else None
        ),
        generado_en=fila["generado_en"],
        paridad_pdf_web=None if fila["paridad_pdf_web"] is None else bool(fila["paridad_pdf_web"]),
    )


def _exigir_publicada(con: sqlite3.Connection, novel_id: str, version: int) -> None:
    if novel.estado_de_obra(con, novel_id=novel_id) is None:
        raise NovelaNoEncontrada(f"no existe la novela {novel_id}", novel_id=novel_id)
    fila = repository.leer_version(con, novel_id=novel_id, version=version)
    if fila is None or fila["estado"] != "publicada":
        raise VersionNoEncontrada(
            f"la novela {novel_id} no tiene la versión {version} publicada", novel_id=novel_id
        )


async def solicitar(db: BaseDatos, novel_id: str, version: int) -> tuple[Exportacion, bool]:
    """El export de la versión y si hay que generarlo ahora. Uno `en-curso` o `disponible`
    se devuelve tal cual; uno `fallido` se relanza (A-119)."""

    def escribir(con: sqlite3.Connection) -> tuple[Exportacion, bool]:
        _exigir_publicada(con, novel_id, version)
        fila = repository.leer_exportacion(con, novel_id=novel_id, version=version)
        if fila is not None and fila["estado"] != "fallido":
            return _vista(fila), False
        repository.iniciar_exportacion(con, novel_id=novel_id, version=version, ahora=ahora())
        nueva = repository.leer_exportacion(con, novel_id=novel_id, version=version)
        assert nueva is not None
        return _vista(nueva), True

    return await db.en_transaccion(escribir)


def _ruta_pdf(db: BaseDatos, novel_id: str, version: int) -> Path:
    return db.ruta.parent / "exports" / novel_id / f"v{version}.pdf"


@dataclass(frozen=True)
class _Entorno:
    db: BaseDatos
    trazador: Trazador
    tolerancia: float
    timeout_s: float


async def _generar(e: _Entorno, novel_id: str, version: int) -> Exportacion:
    lectura_url = os.environ.get("STORYMAKER_LECTURA_URL", "").strip()
    cambios: dict[str, Any]
    with (
        e.trazador.traza("export", novel_id=novel_id, metadata={"version": version}),
        e.trazador.span("export", metadata={"version": version}),
    ):
        try:
            if not lectura_url:
                raise ExportFallido("no hay página de lectura configurada (STORYMAKER_LECTURA_URL)")
            pdf, web = await renderizar(
                lectura.url(lectura_url, novel_id, version), timeout_s=e.timeout_s
            )
        except ExportFallido as fallo:
            cambios = {"estado": "fallido", "detalle": str(fallo)[:2000]}
        else:
            veredicto = paridad.paridad(web, paridad.leer_pdf(pdf), e.tolerancia)
            e.trazador.score(veredicto.nombre, veredicto.valor, comentario=veredicto.detalle)
            ruta = _ruta_pdf(e.db, novel_id, version)
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_bytes(pdf)
            # Un PDF que no dice lo mismo que la web no se entrega (A-121): se guarda
            # para el diagnóstico y el export queda fallido.
            cambios = {
                "estado": "disponible" if veredicto.pasa else "fallido",
                "ruta": str(ruta),
                "generado_en": ahora(),
                "paridad_pdf_web": int(veredicto.pasa),
                "detalle": veredicto.detalle[:2000],
            }

    def cerrar(con: sqlite3.Connection) -> Exportacion:
        repository.cerrar_exportacion(con, novel_id=novel_id, version=version, cambios=cambios)
        fila = repository.leer_exportacion(con, novel_id=novel_id, version=version)
        assert fila is not None
        return _vista(fila)

    return await e.db.en_transaccion(cerrar)


def _entorno(r: Recursos) -> _Entorno:
    return _Entorno(
        db=r.db,
        trazador=r.trazador,
        tolerancia=r.config.umbrales.export.tolerancia_recuento_palabras,
        timeout_s=r.config.umbrales.export.timeout_segundos,
    )


async def generar(r: Recursos, novel_id: str, version: int) -> Exportacion:
    """Genera el PDF de un export `en-curso` y cierra su fila."""
    return await _generar(_entorno(r), novel_id, version)


async def descargar(db: BaseDatos, novel_id: str, version: int) -> Path:
    def leer(con: sqlite3.Connection) -> dict[str, Any] | None:
        return repository.leer_exportacion(con, novel_id=novel_id, version=version)

    fila = await db.ejecutar(leer)
    if fila is None or fila["estado"] != "disponible" or not Path(fila["ruta"]).is_file():
        raise ExportNoDisponible(
            f"la versión {version} de la novela {novel_id} no tiene PDF disponible",
            novel_id=novel_id,
        )
    return Path(fila["ruta"])


def sanear(con: sqlite3.Connection) -> None:
    """Al arrancar: un export `en-curso` no sobrevive a un reinicio (A-120)."""
    repository.interrumpir_exportaciones(con, ahora=ahora())


# --- Línea de comandos (D-22) -----------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.versioning.export")
    parser.add_argument("novel_id")
    parser.add_argument("version", type=int)
    args = parser.parse_args(argv)
    config = cargar_config()
    db = BaseDatos(ruta_db())
    db.ejecutar_sync(aplicar_migraciones)
    trazador = TrazadorLangfuse()
    e = _Entorno(
        db=db,
        trazador=trazador,
        tolerancia=config.umbrales.export.tolerancia_recuento_palabras,
        timeout_s=config.umbrales.export.timeout_segundos,
    )

    async def exportar() -> Exportacion:
        vista, hay_que_generar = await solicitar(db, args.novel_id, args.version)
        return await _generar(e, args.novel_id, args.version) if hay_que_generar else vista

    try:
        vista = anyio.run(exportar)
    finally:
        trazador.cerrar()
    if vista.estado != "disponible":
        fila = db.ejecutar_sync(
            lambda con: repository.leer_exportacion(
                con, novel_id=args.novel_id, version=args.version
            )
        )
        detalle = "" if fila is None else fila["detalle"]
        print(json.dumps({"estado": vista.estado, "detalle": detalle}, ensure_ascii=False))
        return 1
    print(_ruta_pdf(db, args.novel_id, args.version))
    return 0


if __name__ == "__main__":
    sys.exit(main())
