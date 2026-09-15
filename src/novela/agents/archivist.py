"""Archivista y Juez (BUILD_SPEC §7, §9.5).

El Archivista extrae el estado del mundo del capitulo ya cerrado. El Juez evalua
voz, motivacion y tension con un `system` propio y SIN el prompt del Escritor en
contexto, para reducir el sesgo de autoevaluacion.
"""

from __future__ import annotations

import json

from novela.agents.base import JsonAgent
from novela.models import (
    ArchivistOutput,
    ChapterPlan,
    Issue,
    IssueList,
    Ledger,
    StoryBible,
)


def _dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


class Archivist(JsonAgent):
    role = "archivist"

    def run(
        self, text: str, bible: StoryBible, ledger: Ledger, plan: ChapterPlan
    ) -> ArchivistOutput:
        return self.produce(
            template="archivist.md",
            schema=ArchivistOutput,
            chapter=plan.number,
            role_description="el Archivista, responsable del estado del mundo",
            chapter_number=plan.number,
            chapter_text=text,
            bible=_dumps(bible.model_dump(mode="json")),
            ledger=_dumps(ledger.model_dump(mode="json")),
            plan=_dumps(plan.model_dump(mode="json")),
        )


class Judge(JsonAgent):
    role = "judge"

    def run(self, text: str, bible: StoryBible, plan: ChapterPlan) -> list[Issue]:
        voices = {
            character.name: character.voice
            for character in bible.characters
            if character.id == plan.pov_character_id or character.id in plan.location_ids
        } or {character.name: character.voice for character in bible.characters}
        result = self.produce(
            template="judge.md",
            schema=IssueList,
            chapter=plan.number,
            role_description=(
                "el Juez, un evaluador independiente que no ha escrito este capítulo"
            ),
            chapter_number=plan.number,
            chapter_text=text,
            plan=_dumps(plan.model_dump(mode="json")),
            voices=_dumps(voices),
        )
        return result.issues
