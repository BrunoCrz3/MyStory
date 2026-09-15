"""T-10, T-11 y T-12: umbrales null, precedencia y claves desconocidas."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from novela.config import resolve, set_yaml_value
from novela.errors import ConfigError
from novela.validators import repetition


# ---------------------------------------------------------------- T-10
def test_null_thresholds_disable_severity_but_not_the_metric(sandbox: Path) -> None:
    micro = resolve(repo_root=sandbox, environ={}).config
    assert micro.profile == "micro"
    assert micro.repetition.jaccard_blocking is None
    assert micro.repetition.cosine_scene_blocking is None

    text = "El hielo crujía bajo la rejilla del andamio helado.\n"
    report = repetition.validate(
        text,
        previous_texts=[text],
        style_artifacts=[],
        opening_history=[],
        seen_openers=set(),
        cfg=micro.repetition,
        chapter=2,
    )
    # La metrica se calcula aunque el umbral este desactivado.
    assert report.metrics["rep.jaccard_max"] > 0.9
    assert report.metrics["rep.cosine_max"] > 0.9
    assert not report.blocking


def test_full_profile_turns_the_same_metric_into_a_blocking_issue(sandbox: Path) -> None:
    full = resolve(repo_root=sandbox, flags={"profile": "full"}, environ={}).config
    assert full.repetition.jaccard_blocking == 0.15

    text = "El hielo crujía bajo la rejilla del andamio helado del invernadero.\n"
    report = repetition.validate(
        text,
        previous_texts=[text],
        style_artifacts=[],
        opening_history=[],
        seen_openers=set(),
        cfg=full.repetition,
        chapter=2,
    )
    assert "REP-NGRAM" in {issue.code for issue in report.blocking}
    assert report.metrics["rep.jaccard_max"] > 0.9


# ---------------------------------------------------------------- T-11
def test_precedence_from_defaults_to_cli_flags(sandbox: Path) -> None:
    assert resolve(repo_root=sandbox, environ={}).config.novel.chapters == 3

    (sandbox / "novela.yaml").write_text("novel:\n  chapters: 5\n", encoding="utf-8")
    assert resolve(repo_root=sandbox, environ={}).config.novel.chapters == 5

    project = sandbox / "out" / "p1"
    project.mkdir(parents=True)
    (project / "config.yaml").write_text("novel:\n  chapters: 7\n", encoding="utf-8")
    assert resolve(repo_root=sandbox, project_id="p1", environ={}).config.novel.chapters == 7

    env = {"NOVELA__NOVEL__CHAPTERS": "9"}
    assert resolve(repo_root=sandbox, project_id="p1", environ=env).config.novel.chapters == 9

    bundle = resolve(repo_root=sandbox, project_id="p1", environ=env, flags={"novel.chapters": 11})
    assert bundle.config.novel.chapters == 11
    assert bundle.origins["novel.chapters"] == "flags de la CLI"


def test_merge_is_deep_not_block_replacement(sandbox: Path) -> None:
    (sandbox / "novela.yaml").write_text("novel:\n  length:\n    target: 6\n", encoding="utf-8")
    novel = resolve(repo_root=sandbox, environ={}).config.novel
    # Solo se pisa `target`: el resto del bloque `length` se hereda.
    assert (novel.length.target, novel.length.unit, novel.length.tolerance) == (6, "lines", 0)


def test_origins_explain_every_key(sandbox: Path) -> None:
    bundle = resolve(repo_root=sandbox, environ={})
    assert bundle.origins["novel.chapters"] == "config/default.yaml"
    assert bundle.origins["repetition.ngram_size"] == "config/profiles/micro.yaml"


# ---------------------------------------------------------------- T-12
def test_unknown_key_raises_with_suggestion(sandbox: Path) -> None:
    (sandbox / "novela.yaml").write_text("novel:\n  chapter: 5\n", encoding="utf-8")
    with pytest.raises(ConfigError) as error:
        resolve(repo_root=sandbox, environ={})
    message = str(error.value)
    assert "clave desconocida 'novel.chapter'" in message
    assert "novela.yaml" in message
    assert "novel.chapters" in message


@pytest.mark.parametrize(
    "yaml_body",
    [
        "novel:\n  chapters: 100\n",
        "novel:\n  chapters: 2\n",
        "novel:\n  length:\n    unit: paragraphs\n",
        "novel:\n  length:\n    target: 0\n",
        "novel:\n  length:\n    tolerance: -1\n",
    ],
)
def test_out_of_range_values_fail_validation(sandbox: Path, yaml_body: str) -> None:
    (sandbox / "novela.yaml").write_text(yaml_body, encoding="utf-8")
    with pytest.raises(ConfigError, match="configuracion invalida"):
        resolve(repo_root=sandbox, environ={})


def test_unknown_profile_is_loud(sandbox: Path) -> None:
    (sandbox / "novela.yaml").write_text("profile: gigante\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="perfil 'gigante' inexistente"):
        resolve(repo_root=sandbox, environ={})


# ---------------------------------------------------------------- coherencia y escritura
def test_cross_coherence_warnings(sandbox: Path) -> None:
    (sandbox / "novela.yaml").write_text(
        "novel:\n  length:\n    unit: lines\n    target: 2\n", encoding="utf-8"
    )
    assert any(
        "estructura dramática" in item for item in resolve(repo_root=sandbox, environ={}).warnings
    )

    (sandbox / "novela.yaml").write_text(
        "profile: micro\nnovel:\n  length:\n    unit: words\n    target: 500\n    tolerance: 50\n",
        encoding="utf-8",
    )
    assert any(
        "no protegerá la obra" in item for item in resolve(repo_root=sandbox, environ={}).warnings
    )


def test_config_set_preserves_comments(sandbox: Path, repo_root: Path) -> None:
    target = sandbox / "novela.yaml"
    shutil.copyfile(repo_root / "novela.example.yaml", target)
    set_yaml_value(target, "novel.chapters", 24)
    set_yaml_value(target, "novel.length.unit", "words")
    set_yaml_value(target, "limits.context_token_budget", 40000)

    content = target.read_text(encoding="utf-8")
    assert "# Número de capítulos de la novela" in content
    assert "# Perfil de umbrales de calidad" in content

    config = resolve(repo_root=sandbox, environ={}).config
    assert (config.novel.chapters, config.novel.length.unit) == (24, "words")
    # Una clave que no existia en el fichero tambien se escribe correctamente.
    assert config.limits.context_token_budget == 40000
