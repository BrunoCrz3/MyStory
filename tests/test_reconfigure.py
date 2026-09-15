"""T-09 y T-13: cambiar de 3 capítulos de 4 líneas a 5 de 120 palabras.

El criterio del spec es explícito: la única cosa que se toca es el YAML.
Ninguna línea de `src/` cambia, y este fichero no importa nada que no importe
también el pipeline normal. Las fixtures son DATOS DE PRUEBA, no código del
sistema: se generan aquí para alimentar al `FakeLLM`, igual que
`scripts/make_fixtures.py` genera las del repositorio.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from novela.config import resolve, set_yaml_value
from novela.orchestrator.pipeline import Pipeline
from novela.validators.length import count_units

CHAPTERS = 5
TARGET_WORDS = 120
TOLERANCE = 20

#: Vocabulario propio de cada capítulo. Textos con léxico disjunto evitan que el
#: perfil `full` dispare REP-NGRAM y REP-COSINE, que sí son bloqueantes ahí.
CHAPTER_TEXTS: dict[int, list[str]] = {
    1: [
        "El invernadero orbital giraba despacio sobre el terminador del planeta, y la luz "
        "entraba por las lamas en franjas frías que recorrían los bancales de tierra negra.",
        "Marek anotó la temperatura del sustrato, la humedad relativa y el consumo del "
        "circuito de riego en tres columnas distintas del cuaderno de servicio.",
        "Las semillas germinadas mostraban una coloración ocre que ningún manual de botánica "
        "recogía, ni siquiera en los apéndices dedicados a los cultivos de gravedad baja.",
        "Guardó una muestra en un vial precintado, escribió la fecha con rotulador graso y "
        "cerró el armario refrigerado antes de que sonara el aviso del relevo.",
        "Al salir apagó las lamas del sector norte y comprobó que el bancal quedaba en "
        "penumbra, tal como exigía el protocolo de descanso del sustrato.",
    ],
    2: [
        "—Nadie firmó la solicitud de esa variedad, Marek, y sin embargo alguien la sembró "
        "—dijo Irene apoyada en el marco de la compuerta, con el casco bajo el brazo.",
        "El expediente agronómico aparecía completo salvo por la casilla del solicitante, "
        "que llevaba dieciséis meses vacía sin que ninguna auditoría lo señalara.",
        "Irene desplegó el historial de accesos al banco de germoplasma y ordenó las entradas "
        "por franja horaria, buscando coincidencias con los turnos de mantenimiento.",
        "Tres visitas nocturnas compartían la misma credencial genérica, emitida para un "
        "contratista externo cuyo contrato había vencido durante la campaña anterior.",
        "Anotó el número de credencial en un margen del listado, subrayado dos veces, y "
        "pidió al terminal una copia impresa que nadie más pudiera borrar después.",
    ],
    3: [
        "Forzó el cierre magnético del banco de germoplasma con una palanca de servicio, "
        "sabiendo que la maniobra dejaría constancia en el registro de incidencias.",
        "Dentro, las bandejas etiquetadas ocupaban su posición exacta, pero el peso declarado "
        "en el albarán no coincidía con el que devolvía la balanza de la sala.",
        "Faltaban once contenedores de la serie más antigua, sustituidos por réplicas vacías "
        "cuyas etiquetas reproducían los códigos originales con un error tipográfico mínimo.",
        "Irene fotografió cada bandeja y Marek transcribió los códigos a mano, porque el "
        "terminal del banco llevaba semanas exportando ficheros corruptos.",
        "La balanza repitió la medición cuatro veces seguidas y devolvió siempre la misma "
        "diferencia, once kilos exactos por debajo de lo que declaraba el albarán sellado.",
    ],
    4: [
        "Marek recordó entonces la conversación del comedor, cuando el jefe de campaña habló "
        "de cuotas de exportación y de una prima que nadie supo explicar del todo.",
        "La contabilidad del invernadero cuadraba solo si se aceptaba que once contenedores "
        "habían salido del inventario por una merma declarada como pérdida biológica.",
        "Esa merma justificaba un seguro, el seguro justificaba una liquidación anticipada y "
        "la liquidación justificaba el cierre de la campaña seis semanas antes de plazo.",
        "Ninguna de las tres decisiones era ilegal por separado, y esa era exactamente la "
        "razón por la que llevaban dieciséis meses funcionando sin levantar una sola alarma.",
        "Sumó las fechas en el reverso de una hoja de riego y obtuvo un calendario que "
        "encajaba demasiado bien con las visitas nocturnas del contratista externo.",
    ],
    5: [
        "La sala de juntas olía a plástico recién impreso cuando el comité abrió la sesión "
        "extraordinaria con el acta de la auditoría sobre la mesa central.",
        "Marek presentó el vial precintado, las fotografías de las bandejas y la transcripción "
        "manual de los códigos, ordenados por fecha y firmados con su número de empleado.",
        "El jefe de campaña no discutió ninguna cifra: pidió que constara su renuncia y "
        "solicitó que el expediente pasara íntegro al inspector regional.",
        "Irene cerró la carpeta, miró el terminador del planeta a través del ventanal y dijo "
        "que aquella era la primera vez que un papel suyo servía para algo.",
        "Fuera, el anillo seguía girando con la misma indiferencia mecánica de siempre, "
        "ajeno por completo a la firma que acababa de cambiar el destino de la campaña.",
    ],
}

LIMITS = [
    "El invernadero jamás alcanza autonomía térmica fuera de la ventana solar directa.",
    "Ningún cultivo germinado aquí resiste el traslado a gravedad planetaria completa.",
    "La contabilidad automática nunca corrige un albarán ya sellado por el comité.",
]


def _text(number: int) -> str:
    return "\n".join(CHAPTER_TEXTS[number]) + "\n"


def _bible() -> dict[str, object]:
    return {
        "logline": "Dos técnicos de un invernadero orbital descubren que la merma declarada "
        "en el inventario financia el cierre anticipado de la campaña.",
        "theme": "Tres decisiones legales encadenadas producen un fraude que nadie firmó.",
        "characters": [
            {
                "id": "chr_1",
                "name": "Marek Solano",
                "role": "técnico agrónomo",
                "want": "cerrar la campaña con el inventario cuadrado",
                "need": "dejar de fiarse del expediente antes que de la balanza",
                "fear": "que su firma avale una merma inventada",
                "flaw": "anota todo y no pregunta nada",
                "voice": "enumerativa, precisa, sin adjetivos",
                "arc_start": "registra",
                "arc_mid": "contrasta",
                "arc_end": "denuncia",
            },
            {
                "id": "chr_2",
                "name": "Irene Duque",
                "role": "jefa de mantenimiento",
                "want": "que el banco de germoplasma pase la auditoría",
                "need": "aceptar que su credencial genérica abrió la puerta",
                "fear": "quedar como cómplice de algo que no entendió",
                "flaw": "resuelve por su cuenta lo que debería escalar",
                "voice": "directa, interrogativa, impaciente",
                "arc_start": "duda",
                "arc_mid": "investiga",
                "arc_end": "firma",
            },
        ],
        "locations": [
            {
                "id": "loc_1",
                "name": "Invernadero orbital",
                "description": "Anillo de cultivo con lamas orientables y bancales de tierra negra.",
            },
            {
                "id": "loc_2",
                "name": "Banco de germoplasma",
                "description": "Cámara fría con bandejas etiquetadas y balanza de contraste.",
            },
            {
                "id": "loc_3",
                "name": "Sala de juntas",
                "description": "Despacho acristalado orientado al terminador del planeta.",
            },
        ],
        "speculative_premise": {
            "concept": "Un invernadero orbital que cultiva variedades imposibles en superficie.",
            "rules": ["El ciclo de luz depende de la órbita.", "Cada bandeja lleva código único."],
            "limits": LIMITS,
            "cost": "Cada campaña consume la ventana solar de un trimestre completo y no admite "
            "prórroga sin renegociar la concesión entera.",
        },
        "timeline_before": ["La campaña anterior cerró con superávit declarado."],
        "glossary": {"merma": "Pérdida biológica declarada en el inventario de campaña."},
        "motifs": ["las lamas y sus franjas de luz", "códigos escritos a mano"],
    }


def _outline() -> dict[str, object]:
    functions = ["detonante", "investigacion", "descubrimiento", "revelacion", "resolucion"]
    places = ["loc_1", "loc_2", "loc_2", "loc_1", "loc_3"]
    chapters = []
    for number in range(1, CHAPTERS + 1):
        sentences = CHAPTER_TEXTS[number]
        chapters.append(
            {
                "number": number,
                "working_title": f"Campaña {number}",
                "pov_character_id": "chr_1",
                "location_ids": [places[number - 1]],
                "story_time_start": f"jornada {number * 2}, hora 07:00",
                "story_time_end": f"jornada {number * 2}, hora 19:00",
                "dramatic_function": functions[number - 1],
                "goal": f"objetivo del capítulo {number}",
                "conflict": f"conflicto del capítulo {number}",
                "outcome": f"resultado del capítulo {number}",
                # Los beats reproducen frases del capítulo: la cobertura exigida por el
                # perfil `full` es del 90 %, y aquí es del 100 %.
                "scenes": [
                    {
                        "id": f"sc_{number}_1",
                        "beats": [sentences[0], sentences[2]],
                        "new_information": [f"dato nuevo {number}a", f"dato nuevo {number}b"],
                    }
                ],
                "threads_opened": ["th_1"] if number == 1 else [],
                "threads_advanced": ["th_1"] if 1 < number < CHAPTERS else [],
                "threads_closed": ["th_1"] if number == CHAPTERS else [],
                "world_state_delta": [f"delta {number}"],
                "hook": f"gancho del capítulo {number}",
                "target_length": {"unit": "words", "target": TARGET_WORDS, "tolerance": TOLERANCE},
            }
        )
    return {"chapters": chapters}


def _archivist(number: int) -> dict[str, object]:
    thread = {
        "id": "th_1",
        "question": "¿Quién sembró la variedad no solicitada?",
        "opened_chapter": 1,
        "planned_close_chapter": CHAPTERS,
        "closed_chapter": CHAPTERS if number == CHAPTERS else None,
        "status": "cerrado" if number == CHAPTERS else "abierto",
        "importance": "principal",
    }
    return {
        # Un predicado distinto por capítulo: sin hechos vigentes en conflicto.
        "facts": [
            {
                "id": f"f_{number}",
                "subject": "chr_1",
                "predicate": f"registro_{number}",
                "value": f"anotación del capítulo {number}",
                "chapter_established": number,
                "status": "vigente",
                "revoked_by": None,
                "evidence": CHAPTER_TEXTS[number][1][:120],
            }
        ],
        "threads": [thread] if number in (1, CHAPTERS) else [],
        "summary": {
            "number": number,
            "one_line": f"Resumen en una línea del capítulo {number}.",
            "paragraph": f"Párrafo del capítulo {number}. " * 4,
            "by_scene": [f"escena {number}"],
        },
        "style_artifacts": [
            {
                "id": f"sty_{number}",
                "kind": "apertura",
                "text": f"apertura propia del capítulo {number}",
                "chapter": number,
            }
        ],
        "new_entities": ["Marek Solano", "Irene Duque"] if number == 1 else [],
    }


def _write_fixtures(sandbox: Path) -> None:
    directory = sandbox / "fixtures" / "llm"
    for path in directory.glob("*.json"):
        path.unlink()

    def dump(name: str, payload: dict[str, object]) -> None:
        (directory / f"{name}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    dump("architect", {"role": "architect", "output_type": "json", "json": _bible()})
    dump("outliner", {"role": "outliner", "output_type": "json", "json": _outline()})
    for number in range(1, CHAPTERS + 1):
        dump(f"writer_ch{number}", {"role": "writer", "output_type": "text", "text": _text(number)})
        dump(
            f"archivist_ch{number}",
            {"role": "archivist", "output_type": "json", "json": _archivist(number)},
        )
    dump("judge_clean", {"role": "judge", "output_type": "json", "json": {"issues": []}})
    dump(
        "reviewer",
        {
            "role": "reviewer",
            "output_type": "json",
            "json": {
                "novel_title": "Merma declarada",
                "synopsis": "Dos técnicos reconstruyen el fraude a partir de una balanza.",
                "chapter_titles": {str(n): f"Campaña {n}" for n in range(1, CHAPTERS + 1)},
                "corrections": [],
                "pacing_notes": ["El tramo central se sostiene en la comparación de registros."],
            },
        },
    )


@pytest.fixture
def reconfigured(sandbox: Path, repo_root: Path) -> Path:
    """Sandbox con novela.yaml reescrito SOLO por YAML y fixtures de 5 capítulos."""
    import shutil

    target = sandbox / "novela.yaml"
    shutil.copyfile(repo_root / "novela.example.yaml", target)
    set_yaml_value(target, "novel.chapters", CHAPTERS)
    set_yaml_value(target, "novel.length.unit", "words")
    set_yaml_value(target, "novel.length.target", TARGET_WORDS)
    set_yaml_value(target, "novel.length.tolerance", TOLERANCE)
    set_yaml_value(target, "profile", "full")
    _write_fixtures(sandbox)
    return sandbox


# ---------------------------------------------------------------- T-09
def test_fixture_chapters_are_within_the_new_bounds() -> None:
    """Comprobación previa: los datos de prueba cumplen el contrato que se va a validar."""
    for number in range(1, CHAPTERS + 1):
        counted = count_units(_text(number), "words")
        assert TARGET_WORDS - TOLERANCE <= counted <= TARGET_WORDS + TOLERANCE, (
            f"el capítulo {number} tiene {counted} palabras"
        )


def test_only_the_yaml_changes_the_whole_pipeline(reconfigured: Path) -> None:
    bundle = resolve(repo_root=reconfigured, environ={})
    assert bundle.config.novel.chapters == CHAPTERS
    assert bundle.config.profile == "full"
    assert bundle.config.novel.length.bounds() == (100, 140)

    pipeline = Pipeline.open(bundle.config, reconfigured, "big")
    pipeline.init("Una premisa de invernadero.", resolved_yaml="project: {}\n")
    produced = pipeline.run_auto()

    versions = pipeline.store.all_chapters()
    assert [version.number for version in versions] == list(range(1, CHAPTERS + 1))
    for version in versions:
        assert 100 <= version.unit_count <= 140, (
            f"el capítulo {version.number} tiene {version.unit_count} palabras"
        )
    assert produced["md"].is_file()


def test_the_full_profile_thresholds_are_actually_in_force(reconfigured: Path) -> None:
    config = resolve(repo_root=reconfigured, environ={}).config
    assert config.repetition.jaccard_blocking == 0.15
    assert config.repetition.ngram_size == 4
    assert config.continuity.beat_coverage_min == 0.90
    assert config.context.mid_summaries is True
    assert config.context.rag_top_k == 5


# ---------------------------------------------------------------- T-13
def test_editing_the_yaml_between_invocations_changes_behaviour(sandbox: Path) -> None:
    """La configuración se relee en cada invocación: no hay nada que reiniciar."""
    target = sandbox / "novela.yaml"
    target.write_text("novel:\n  chapters: 3\n", encoding="utf-8")
    assert resolve(repo_root=sandbox, environ={}).config.novel.chapters == 3

    set_yaml_value(target, "novel.chapters", 8)
    assert resolve(repo_root=sandbox, environ={}).config.novel.chapters == 8


def test_changing_chapters_after_the_outline_warns_and_does_not_truncate(
    sandbox: Path,
) -> None:
    bundle = resolve(repo_root=sandbox, environ={})
    pipeline = Pipeline.open(bundle.config, sandbox, "drift")
    pipeline.init("Una premisa.", resolved_yaml="project: {}\n")
    pipeline.build_bible()
    outline, _ = pipeline.build_outline()
    assert len(outline.chapters) == 3

    # El usuario sube N con la escaleta ya aprobada.
    (sandbox / "novela.yaml").write_text("novel:\n  chapters: 5\n", encoding="utf-8")
    updated = resolve(repo_root=sandbox, environ={}).config
    reopened = Pipeline.open(updated, sandbox, "drift")

    stored, report = reopened.build_outline()
    # No se trunca ni se improvisa: la escaleta sigue teniendo 3 capítulos…
    assert len(stored.chapters) == 3
    # …y el validador lo declara bloqueante hasta que se regenere explícitamente.
    assert "OUT-WRONG-COUNT" in {issue.code for issue in report.blocking}


def test_regenerating_the_outline_applies_the_new_chapter_count(reconfigured: Path) -> None:
    bundle = resolve(repo_root=reconfigured, environ={})
    pipeline = Pipeline.open(bundle.config, reconfigured, "regen")
    pipeline.init("Una premisa.", resolved_yaml="project: {}\n")
    pipeline.build_bible()
    outline, report = pipeline.build_outline(regenerate=True)
    assert len(outline.chapters) == CHAPTERS
    assert report.blocking == []
