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


def test_nadie_llama_al_modelo_sin_pasar_por_el_llamador() -> None:
    assert c.violaciones_camino_al_modelo() == []


def test_meta_llamada_directa_al_cliente(tmp_path: Path) -> None:
    _escribir(tmp_path, "process/service.py", "async def f(c, p):\n    await c.generar(p, 1)\n")
    assert c.violaciones_camino_al_modelo(tmp_path)


def test_ningun_camino_ejecuta_la_salida_del_modelo() -> None:
    """RNF-09: nada en `app/` llama a `eval`, `exec` ni `os.system`, y el único proceso que
    se lanza es el CLI del proveedor `claude_code`, con argumentos propios y la petición por
    la entrada estándar (TO-040). La salida del modelo es prosa que se guarda."""
    assert c.violaciones_ejecucion() == []


def test_meta_ejecucion_caza_eval_os_system_y_procesos(tmp_path: Path) -> None:
    raiz = tmp_path / "app"
    (raiz / "quality").mkdir(parents=True)
    codigo = [
        "import os",
        "import subprocess",
        "def f(x):",
        "    eval(x)",
        "    os.system(x)",
        "    subprocess.run([x])",
    ]
    (raiz / "quality" / "malo.py").write_text("\n".join(codigo), encoding="utf-8")
    assert len(c.violaciones_ejecucion(raiz)) == 3
