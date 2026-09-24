"""Prompts por rol, su hash de git y la skill de runtime (RF-OBS-05, TO-021, TO-024)."""

from __future__ import annotations

import re
import subprocess

import pytest

from app.prompts import PROMPT_DE_ROL, SKILLS_DE_ROL, cargar_prompt, cargar_skill
from app.prompts.sync import LIMITE_ETIQUETA_LANGFUSE, etiqueta_git, sincronizar
from tests.arquitectura.comprobadores import RAIZ_APP, RAIZ_REPO
from tests.dobles.prompts import RegistroPromptsEnMemoria
from tests.fixtures.briefs import brief_ejemplo


def _hash_git(ruta: str) -> str:
    return subprocess.run(
        ["git", "hash-object", ruta], cwd=RAIZ_REPO, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.mark.parametrize("rol", list(PROMPT_DE_ROL))
def test_el_hash_es_el_de_git_del_fichero_usado(rol: str) -> None:
    prompt = cargar_prompt(PROMPT_DE_ROL[rol])  # type: ignore[index]
    assert prompt.hash_git == _hash_git(str(prompt.ruta))
    assert prompt.texto == prompt.ruta.read_text(encoding="utf-8")


def test_hay_un_prompt_por_rol() -> None:
    assert set(PROMPT_DE_ROL.values()) == {
        "interviewer",
        "planner",
        "writer",
        "judge",
        "editor",
        "extractor",
    }


def test_la_skill_la_cargan_planner_writer_y_editor() -> None:
    con = {rol for rol, skills in SKILLS_DE_ROL.items() if "personalizacion-natural" in skills}
    assert con == {"planificador", "redactor", "editor"}
    assert "Tejido frente a insertado" in cargar_skill("personalizacion-natural").texto


def _lineas_de_rubrica() -> list[str]:
    judge = cargar_prompt("judge").texto
    seccion = judge.split("## Rúbrica", 1)[1].split("\n## ", 1)[0]
    return [ln.strip() for ln in seccion.splitlines() if ln.strip().startswith("- **")]


def test_la_skill_no_tiene_cifras_ni_rubrica() -> None:
    skill = cargar_skill("personalizacion-natural").texto
    cuerpo = skill.split("---", 2)[2]
    assert not re.search(r"\d", cuerpo), "la skill no puede contener anclas numéricas"
    for linea in _lineas_de_rubrica():
        assert linea not in skill


@pytest.mark.parametrize("nombre", ["writer", "editor", "planner"])
def test_la_rubrica_solo_esta_en_el_judge(nombre: str) -> None:
    texto = cargar_prompt(nombre).texto
    assert _lineas_de_rubrica()
    for linea in _lineas_de_rubrica():
        assert linea not in texto
    assert "## Rúbrica" not in texto


def test_ningun_prompt_contiene_datos_de_una_novela() -> None:
    brief = brief_ejemplo()
    sensibles = [
        brief["destinatario"]["nombre"],
        brief["dedicatoria"]["texto"],
        *[e["enunciado"] for e in brief["elementos_personalizados"]],
    ]
    for fichero in (RAIZ_APP / "prompts").glob("*.md"):
        texto = fichero.read_text(encoding="utf-8")
        for dato in sensibles:
            assert dato not in texto, f"{fichero.name} contiene un dato de novela"


def test_sync_es_idempotente_por_hash() -> None:
    registro = RegistroPromptsEnMemoria()
    primera = sincronizar(registro)
    segunda = sincronizar(registro)
    assert len(primera) == len(PROMPT_DE_ROL)
    assert segunda == []
    assert len(registro.publicados) == len(PROMPT_DE_ROL)
    assert all(p.hash_git in registro.etiquetas[p.nombre] for p in registro.publicados)


def test_la_etiqueta_de_version_cabe_en_el_limite_de_langfuse() -> None:
    # Langfuse rechaza con 400 una etiqueta de más de 36 caracteres, y `git-` más el hash
    # completo de 40 ocupa 44: la sincronización real falló así en el P27.
    prompt = cargar_prompt("writer")
    etiqueta = etiqueta_git(prompt.hash_git)
    assert len(etiqueta) <= LIMITE_ETIQUETA_LANGFUSE == 36
    assert etiqueta.startswith("git-") and prompt.hash_git.startswith(etiqueta[4:])
