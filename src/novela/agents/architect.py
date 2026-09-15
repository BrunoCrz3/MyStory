"""Arquitecto: premisa + parametros -> StoryBible (BUILD_SPEC §7)."""

from __future__ import annotations

from novela.agents.base import JsonAgent
from novela.models import StoryBible


class Architect(JsonAgent):
    role = "architect"

    def run(self, premise: str) -> StoryBible:
        novel = self.context.config.novel
        return self.produce(
            template="architect.md",
            schema=StoryBible,
            role_description="el Arquitecto, responsable del canon de la obra",
            premise=premise,
            chapter_count=novel.chapters,
            length_spec=novel.length,
        )
