"""Escaletista: StoryBible + N + LengthSpec -> Outline (BUILD_SPEC §7)."""

from __future__ import annotations

import json

from novela.agents.base import JsonAgent
from novela.models import Outline, StoryBible


class Outliner(JsonAgent):
    role = "outliner"

    def run(self, bible: StoryBible) -> Outline:
        novel = self.context.config.novel
        return self.produce(
            template="outliner.md",
            schema=Outline,
            role_description="el Escaletista, responsable del plan capítulo a capítulo",
            bible=json.dumps(bible.model_dump(mode="json"), ensure_ascii=False, indent=2),
            chapter_count=novel.chapters,
            length_spec=novel.length,
        )
