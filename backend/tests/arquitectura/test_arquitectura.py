"""Reglas de `CLAUDE.md` y `docs/architecture.md` comprobadas sobre el código (P02).

Con `app/` casi vacía pasan: vigilan los pasos siguientes. Las meta-pruebas escriben un
árbol con cada violación y comprueban que su regla la caza.
"""

from __future__ import annotations

from pathlib import Path

from tests.arquitectura import comprobadores as c


def test_importaciones_respetan_el_grafo_de_architecture() -> None:
    assert c.violaciones_importacion() == []


def test_el_grafo_de_architecture_incluye_las_aristas_de_d08() -> None:
    aristas = c.aristas_permitidas()
    for arista in [
        ("novel", "intake"),
        ("novel", "guardrail"),
        ("context", "intake"),
        ("context", "guardrail"),
        ("quality", "intake"),
        ("versioning", "intake"),
    ]:
        assert arista in aristas


def test_sin_dobles_en_produccion() -> None:
    assert c.violaciones_dobles() == []


def test_sin_dependencias_excluidas() -> None:
    assert c.violaciones_dependencias() == []


def test_parametros_de_dominio_obligatorios() -> None:
    assert c.violaciones_parametros() == []


# --- Meta-pruebas -----------------------------------------------------------------------


def _escribir(raiz: Path, relativo: str, contenido: str) -> None:
    destino = raiz / relativo
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(contenido, encoding="utf-8")


def test_meta_importar_repository_ajeno(tmp_path: Path) -> None:
    _escribir(tmp_path, "context/service.py", "from app.canon.repository import x\n")
    assert c.violaciones_importacion(tmp_path, {("context", "canon")})


def test_meta_arista_no_declarada(tmp_path: Path) -> None:
    _escribir(tmp_path, "canon/service.py", "from app.process import service\n")
    assert c.violaciones_importacion(tmp_path, set())


def test_meta_ciclo(tmp_path: Path) -> None:
    _escribir(tmp_path, "canon/service.py", "from app.novel import service\n")
    _escribir(tmp_path, "novel/service.py", "from app.canon import service\n")
    problemas = c.violaciones_importacion(tmp_path, {("canon", "novel"), ("novel", "canon")})
    assert any("ciclo" in p for p in problemas)


def test_meta_hoja_que_importa_otra_feature(tmp_path: Path) -> None:
    _escribir(tmp_path, "intake/service.py", "from app.novel import service\n")
    assert c.violaciones_importacion(tmp_path, {("intake", "novel")})


def test_meta_commons_que_importa_una_feature(tmp_path: Path) -> None:
    _escribir(tmp_path, "commons/db.py", "from app.canon import service\n")
    assert c.violaciones_importacion(tmp_path, set())


def test_meta_mock_en_produccion(tmp_path: Path) -> None:
    _escribir(tmp_path, "canon/service.py", "from unittest.mock import MagicMock\n")
    _escribir(tmp_path, "canon/modelo_fake.py", "X = 1\n")
    assert len(c.violaciones_dobles(tmp_path)) == 2


def test_meta_dependencia_excluida(tmp_path: Path) -> None:
    lock = tmp_path / "uv.lock"
    lock.write_text('[[package]]\nname = "sqlalchemy"\nversion = "2.0"\n', encoding="utf-8")
    assert c.violaciones_dependencias(lock)


def test_meta_parametros(tmp_path: Path) -> None:
    _escribir(
        tmp_path,
        "canon/repository.py",
        "def sin_novela(x): ...\n"
        "def con_defecto(*, novel_id=None): ...\n"
        "def versionada(*, novel_id):\n    return 'SELECT * FROM hecho'\n"
        "CONSULTAS_TRANSVERSALES = {'todas'}\n"
        "def todas(): ...\n",
    )
    problemas = c.violaciones_parametros(tmp_path)
    assert len(problemas) == 3, problemas
