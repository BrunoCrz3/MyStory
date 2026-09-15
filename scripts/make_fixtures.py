#!/usr/bin/env python3
"""Regenera las fixtures deterministas del `FakeLLM` (BUILD_SPEC §21.6).

Este fichero es la fuente unica del contenido de `fixtures/llm/`. La coherencia
cruzada es el criterio de aceptacion mas facil de incumplir del inventario: los
hechos del Archivista tienen que corresponder al texto del Escritor del mismo
capitulo, la escaleta tiene que referenciar personajes que existen en la biblia
y los tres capitulos tienen que tener exactamente cuatro lineas.

Al terminar, el script comprueba esas tres cosas y falla si alguna no se cumple.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures" / "llm"

LENGTH = {"unit": "lines", "target": 4, "tolerance": 0}

BIBLE = {
    "logline": (
        "En una estación minera de Encélado, una ingeniera descubre que el oráculo capaz de "
        "anticipar accidentes lleva meses sirviendo para provocarlos."
    ),
    "theme": "Conocer el futuro no es lo mismo que tener permiso para cambiarlo.",
    "characters": [
        {
            "id": "chr_1",
            "name": "Nadia Ferrán",
            "role": "ingeniera de sistemas de la estación",
            "want": "terminar la campaña de extracción sin una sola baja",
            "need": "dejar de obedecer protocolos cuyo motivo nadie le explica",
            "fear": "firmar con su nombre un parte que esconda una muerte",
            "flaw": "confía antes en la lectura de un sensor que en la voz de una persona",
            "voice": "frases cortas, léxico técnico, ironía seca cuando está asustada",
            "arc_start": "cumple el protocolo y anota las anomalías sin discutirlas",
            "arc_mid": "obedece una orden que la deja a ciegas y entiende el precio",
            "arc_end": "documenta la verdad y firma el parte con su nombre",
        },
        {
            "id": "chr_2",
            "name": "Teo Marchetti",
            "role": "supervisor de la concesión minera",
            "want": "sostener la cuota trimestral que renueva la concesión",
            "need": "reconocer que convirtió una herramienta de seguridad en un calendario",
            "fear": "perder la concesión y con ella la única vida que sabe llevar",
            "flaw": "transforma cualquier duda ajena en una orden directa",
            "voice": "imperativos breves, cortesía fría, nunca levanta la voz",
            "arc_start": "administra las consultas del oráculo como un recurso más",
            "arc_mid": "gasta cargas sin justificar y presiona para que nadie mire el registro",
            "arc_end": "explica sus cuentas sin negar nada y acepta quedar por escrito",
        },
    ],
    "locations": [
        {
            "id": "loc_1",
            "name": "Pasarela Seis",
            "description": (
                "Pasillo exterior de rejilla sobre la grieta de extracción, con presión "
                "marginal y dos sellos de emergencia que nunca se han probado."
            ),
        },
        {
            "id": "loc_2",
            "name": "Sala del Oráculo",
            "description": (
                "Cámara blindada donde la red de sensores cuánticos proyecta el interior "
                "de la estación sobre una placa de niebla luminosa."
            ),
        },
    ],
    "speculative_premise": {
        "concept": (
            "El Oráculo es una red de sensores cuánticos que proyecta el estado interior de "
            "la estación noventa segundos por delante del presente."
        ),
        "rules": [
            "Proyecta únicamente lo que ocurre dentro del casco presurizado.",
            "Cada consulta agota una carga de helio-3 que tarda noventa minutos en reponerse.",
            "La proyección es muda: da imagen, nunca sonido ni intención.",
        ],
        "limits": [
            "Ninguna proyección alcanza un horizonte superior al minuto y medio.",
            "El sistema jamás muestra lo que sucede fuera del casco presurizado.",
            "Una decisión todavía no tomada resulta invisible para el aparato.",
        ],
        "cost": (
            "Cada consulta deja al Oráculo inerte durante noventa minutos, y a la estación "
            "sin ningún aviso anticipado mientras dura esa ceguera."
        ),
    },
    "timeline_before": [
        "El Oráculo se instaló catorce meses antes del primer capítulo.",
        "Dos mineros murieron en la Pasarela Seis durante la campaña anterior.",
        "La concesión se renueva por cuota trimestral desde hace seis años.",
    ],
    "glossary": {
        "Oráculo": "Red de sensores cuánticos de anticipación instalada en la cámara blindada.",
        "carga": "Unidad de helio-3 que consume una consulta completa del Oráculo.",
        "parte": "Registro firmado de incidencias de un turno de extracción.",
    },
    "motifs": [
        "el hielo que cruje bajo la rejilla",
        "los guantes y sus sellos",
        "partes firmados y partes en blanco",
    ],
}

CHAPTERS: list[dict[str, object]] = [
    {
        "number": 1,
        "working_title": "Parte en blanco",
        "location_ids": ["loc_1"],
        "story_time_start": "turno 412, hora 06:00",
        "story_time_end": "turno 412, hora 09:20",
        "dramatic_function": "detonante",
        "goal": "cerrar el turno de inspección sin incidencias",
        "conflict": "la proyección muestra una víctima que todavía no existe",
        "outcome": "Nadia deja el parte sin firmar y baja a comprobarlo",
        "hook": "el cuerpo proyectado llevaba su mismo modelo de guante",
        "text": (
            "El hielo de Encélado crujía bajo la rejilla como un hueso que se acomoda.\n"
            "Nadia revisó el sello del guante izquierdo y anotó la microfuga en el parte del turno.\n"
            "Desde la cámara contigua, el Oráculo proyectó una rejilla vacía y un cuerpo que "
            "todavía no existía.\n"
            "Cerró el parte sin firmarlo y bajó a la Pasarela Seis con la linterna apagada.\n"
        ),
        "beats": [
            "Nadia revisa el sello del guante y anota la microfuga en el parte del turno.",
            "El Oráculo proyecta una rejilla vacía con un cuerpo que todavía no existía.",
        ],
        "new_information": [
            "El Oráculo puede proyectar una muerte que aún no ha ocurrido.",
            "El guante de Nadia tiene una microfuga registrada por escrito.",
        ],
    },
    {
        "number": 2,
        "working_title": "La última carga",
        "location_ids": ["loc_2"],
        "story_time_start": "turno 413, hora 05:40",
        "story_time_end": "turno 413, hora 08:10",
        "dramatic_function": "complicacion",
        "goal": "conservar una carga de reserva para el descenso",
        "conflict": "Teo ordena gastarla en una consulta que nadie ha justificado",
        "outcome": "la estación queda sin anticipación durante noventa minutos",
        "hook": "unos pasos conocían de memoria el horario de la ceguera",
        "text": (
            "—Consulta el Oráculo, Nadia, y no discutas la orden —dijo Teo desde el umbral.\n"
            "La reserva de helio-3 bastaba para una sola proyección, y el supervisor ya había "
            "gastado dos esa misma semana.\n"
            "Ella obedeció, y durante hora y media la estación entera quedó tan ciega como su "
            "ingeniera.\n"
            "En la penumbra del pasillo alguien caminó hacia la esclusa con el paso de quien "
            "conoce los horarios.\n"
        ),
        "beats": [
            "Teo ordena a Nadia consultar el Oráculo y gastar la reserva de helio-3.",
            "La estación queda ciega hora y media y alguien camina hacia la esclusa.",
        ],
        "new_information": [
            "Teo ha gastado dos cargas sin dejar justificación en el parte.",
            "Alguien se mueve por la estación justamente durante las ventanas de ceguera.",
        ],
    },
    {
        "number": 3,
        "working_title": "El registro",
        "location_ids": ["loc_2"],
        "story_time_start": "turno 414, hora 04:00",
        "story_time_end": "turno 414, hora 07:30",
        "dramatic_function": "climax_y_resolucion",
        "goal": "abrir el mamparo antes de que el supervisor lo impida",
        "conflict": "lo que guarda el mamparo compromete la concesión entera",
        "outcome": "Nadia se queda el registro y firma el parte pendiente",
        "hook": "una firma bastaba para convertir el silencio en prueba",
        "text": (
            "Arrancó el panel del mamparo con las dos manos antes de que Teo alcanzara la "
            "escotilla.\n"
            "Dentro aguardaba un registro de consultas que nadie había solicitado, fechado en "
            "la campaña de las dos muertes.\n"
            "Teo no negó nada: enumeró la cuota, los plazos y el precio exacto de una concesión "
            "perdida.\n"
            "Ella guardó el registro en el bolsillo del traje y firmó, por fin, aquel primer "
            "parte pendiente.\n"
        ),
        "beats": [
            "Nadia arranca el panel del mamparo y encuentra un registro de consultas no solicitado.",
            "Teo enumera la cuota, los plazos y el precio de una concesión perdida.",
        ],
        "new_information": [
            "Existe un registro fechado de consultas durante la campaña de las dos muertes.",
            "Teo reconoce el móvil económico sin negar los hechos.",
        ],
    },
]

THREAD = {
    "id": "th_1",
    "question": "¿Quién usaba las ventanas de ceguera del Oráculo y para qué?",
    "opened_chapter": 1,
    "planned_close_chapter": 3,
}

# Un hecho de ubicación por capítulo, revocando el anterior: los hechos se
# revocan, nunca se borran (§26.2).
LOCATION_FACTS = [
    ("f_1_loc", 1, "Pasarela Seis", "bajó a la Pasarela Seis con la linterna apagada"),
    ("f_2_loc", 2, "Sala del Oráculo", "Consulta el Oráculo, Nadia, y no discutas la orden"),
    ("f_3_loc", 3, "Sala del Oráculo", "Arrancó el panel del mamparo con las dos manos"),
]

EXTRA_FACTS: dict[int, list[dict[str, object]]] = {
    1: [
        {
            "id": "f_1_guante",
            "subject": "chr_1",
            "predicate": "posee",
            "value": "un guante izquierdo con microfuga registrada",
            "evidence": "revisó el sello del guante izquierdo y anotó la microfuga",
        }
    ],
    2: [
        {
            "id": "f_2_cargas",
            "subject": "chr_2",
            "predicate": "sabe",
            "value": "que ha gastado dos cargas sin justificarlas en el parte",
            "evidence": "el supervisor ya había gastado dos esa misma semana",
        }
    ],
    3: [
        {
            "id": "f_3_registro",
            "subject": "chr_1",
            "predicate": "posee",
            "value": "el registro de consultas no solicitadas de la campaña anterior",
            "evidence": "guardó el registro en el bolsillo del traje",
        }
    ],
}

STYLE_ARTIFACTS: dict[int, list[dict[str, object]]] = {
    1: [
        {"id": "sty_1_a", "kind": "metafora", "text": "como un hueso que se acomoda"},
        {"id": "sty_1_b", "kind": "apertura", "text": "descripcion del entorno helado"},
    ],
    2: [
        {"id": "sty_2_a", "kind": "imagen", "text": "la estación ciega durante hora y media"},
        {"id": "sty_2_b", "kind": "apertura", "text": "dialogo con orden directa del supervisor"},
    ],
    3: [
        {"id": "sty_3_a", "kind": "imagen", "text": "un mamparo arrancado con las dos manos"},
        {"id": "sty_3_b", "kind": "apertura", "text": "accion fisica en primera posicion"},
    ],
}

SUMMARIES = {
    1: (
        "El Oráculo anticipa un cadáver en la Pasarela Seis y Nadia se niega a firmar el parte.",
        "Durante una inspección rutinaria de la Pasarela Seis, Nadia Ferrán registra una "
        "microfuga en su guante izquierdo. La proyección del Oráculo le devuelve la misma "
        "rejilla con un cuerpo que todavía no existe. Deja el parte sin firmar y baja a "
        "comprobarlo por su cuenta.",
    ),
    2: (
        "Teo obliga a gastar la última carga y la estación queda ciega noventa minutos.",
        "Teo Marchetti ordena una consulta que agota la reserva de helio-3. Nadia obedece y "
        "la estación pierde toda anticipación durante hora y media. En esa ventana alguien "
        "recorre el pasillo hacia la esclusa con la seguridad de quien conoce los horarios.",
    ),
    3: (
        "El mamparo guarda el registro de consultas y Teo confiesa el motivo económico.",
        "Nadia arranca el panel del mamparo y encuentra un registro de consultas que nadie "
        "había solicitado, fechado en la campaña de las dos muertes. Teo no lo niega: enumera "
        "la cuota, los plazos y el precio de perder la concesión. Nadia se queda la prueba y "
        "firma por fin el parte del primer turno.",
    ),
}


def build_outline() -> dict[str, object]:
    chapters = []
    for spec in CHAPTERS:
        number = int(spec["number"])
        chapters.append(
            {
                "number": number,
                "working_title": spec["working_title"],
                "pov_character_id": "chr_1",
                "location_ids": spec["location_ids"],
                "story_time_start": spec["story_time_start"],
                "story_time_end": spec["story_time_end"],
                "dramatic_function": spec["dramatic_function"],
                "goal": spec["goal"],
                "conflict": spec["conflict"],
                "outcome": spec["outcome"],
                "scenes": [
                    {
                        "id": f"sc_{number}_1",
                        "beats": spec["beats"],
                        "new_information": spec["new_information"],
                    }
                ],
                "threads_opened": [THREAD["id"]] if number == 1 else [],
                "threads_advanced": [THREAD["id"]] if number == 2 else [],
                "threads_closed": [THREAD["id"]] if number == 3 else [],
                "world_state_delta": [
                    str(item) for item in list(spec["new_information"])  # type: ignore[arg-type]
                ],
                "hook": spec["hook"],
                "target_length": LENGTH,
            }
        )
    return {"chapters": chapters}


def build_archivist(number: int) -> dict[str, object]:
    facts: list[dict[str, object]] = []
    for index, (fact_id, chapter, value, evidence) in enumerate(LOCATION_FACTS):
        if chapter > number:
            continue
        superseded = chapter < number
        successor = LOCATION_FACTS[index + 1][0] if superseded else None
        facts.append(
            {
                "id": fact_id,
                "subject": "chr_1",
                "predicate": "ubicacion",
                "value": value,
                "chapter_established": chapter,
                "status": "revocado" if superseded else "vigente",
                "revoked_by": successor,
                "evidence": evidence,
            }
        )
    for extra in EXTRA_FACTS[number]:
        facts.append({**extra, "chapter_established": number, "status": "vigente", "revoked_by": None})

    thread = dict(THREAD)
    if number == 1:
        thread |= {"status": "abierto", "closed_chapter": None, "importance": "principal"}
        threads = [thread]
    elif number == 3:
        thread |= {"status": "cerrado", "closed_chapter": 3, "importance": "principal"}
        threads = [thread]
    else:
        threads = []

    one_line, paragraph = SUMMARIES[number]
    spec = next(item for item in CHAPTERS if item["number"] == number)
    return {
        "facts": facts,
        "threads": threads,
        "summary": {
            "number": number,
            "one_line": one_line,
            "paragraph": paragraph,
            "by_scene": [str(beat) for beat in list(spec["beats"])],  # type: ignore[arg-type]
        },
        "style_artifacts": [
            {**artifact, "chapter": number} for artifact in STYLE_ARTIFACTS[number]
        ],
        "new_entities": ["Nadia Ferrán", "Teo Marchetti", "Pasarela Seis", "Sala del Oráculo"]
        if number == 1
        else [],
    }


def build_reviewer() -> dict[str, object]:
    return {
        "novel_title": "Noventa segundos de ceguera",
        "synopsis": (
            "Una ingeniera de Encélado descubre que el oráculo instalado para prever accidentes "
            "se ha convertido en el calendario de quien los provoca, y decide firmar por fin "
            "el parte que nadie quería en el registro."
        ),
        "chapter_titles": {
            "1": "Parte en blanco",
            "2": "La última carga",
            "3": "El registro",
        },
        "corrections": [],
        "pacing_notes": [
            "El capítulo 1 sostiene la tensión con una sola anomalía concreta y no adelanta la causa.",
            "El capítulo 2 gasta el recurso escaso y convierte la ceguera en una ventana de oportunidad.",
            "El capítulo 3 cierra el hilo con una prueba material, no con una explicación.",
        ],
    }


def write(name: str, payload: dict[str, object]) -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    path = FIXTURES / f"{name}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def generate() -> None:
    write("architect", {"role": "architect", "output_type": "json", "json": BIBLE})
    write("outliner", {"role": "outliner", "output_type": "json", "json": build_outline()})
    for spec in CHAPTERS:
        number = int(spec["number"])
        write(
            f"writer_ch{number}",
            {
                "role": "writer",
                "chapter": number,
                "output_type": "text",
                "text": spec["text"],
            },
        )
        write(
            f"archivist_ch{number}",
            {
                "role": "archivist",
                "chapter": number,
                "output_type": "json",
                "json": build_archivist(number),
            },
        )
    write("judge_clean", {"role": "judge", "output_type": "json", "json": {"issues": []}})
    write("reviewer", {"role": "reviewer", "output_type": "json", "json": build_reviewer()})


def verify() -> list[str]:
    """Comprobacion de coherencia cruzada. Es el criterio de aceptacion de §21.6."""
    sys.path.insert(0, str(ROOT / "src"))
    from novela.models import ArchivistOutput, GlobalReview, Outline, StoryBible
    from novela.validators.length import count_units

    problems: list[str] = []
    bible = StoryBible.model_validate(json.loads((FIXTURES / "architect.json").read_text("utf-8"))["json"])
    outline = Outline.model_validate(json.loads((FIXTURES / "outliner.json").read_text("utf-8"))["json"])
    GlobalReview.model_validate(json.loads((FIXTURES / "reviewer.json").read_text("utf-8"))["json"])

    character_ids = {character.id for character in bible.characters}
    location_ids = {location.id for location in bible.locations}
    for plan in outline.chapters:
        if plan.pov_character_id not in character_ids:
            problems.append(f"ch{plan.number}: POV '{plan.pov_character_id}' no existe en la biblia")
        for location_id in plan.location_ids:
            if location_id not in location_ids:
                problems.append(f"ch{plan.number}: localización '{location_id}' no existe")

        payload = json.loads((FIXTURES / f"writer_ch{plan.number}.json").read_text("utf-8"))
        text = str(payload["text"])
        counted = count_units(text, plan.target_length.unit)
        if counted != plan.target_length.target:
            problems.append(
                f"ch{plan.number}: el texto tiene {counted} {plan.target_length.unit}, "
                f"se esperaban {plan.target_length.target}"
            )

        archivist = ArchivistOutput.model_validate(
            json.loads((FIXTURES / f"archivist_ch{plan.number}.json").read_text("utf-8"))["json"]
        )
        if archivist.summary.number != plan.number:
            problems.append(f"ch{plan.number}: el resumen del Archivista apunta a otro capítulo")
        if not archivist.facts:
            problems.append(f"ch{plan.number}: el Archivista no aporta ningún CanonFact")
        lowered = text.lower()
        for fact in archivist.facts:
            if fact.chapter_established != plan.number:
                continue
            head = " ".join(fact.evidence.lower().split()[:4])
            if head and head not in lowered:
                problems.append(
                    f"ch{plan.number}: la evidencia de '{fact.id}' no aparece en el texto"
                )
    return problems


def main() -> int:
    generate()
    problems = verify()
    if problems:
        print("Fixtures incoherentes:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print(f"Fixtures regeneradas y coherentes en {FIXTURES.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
