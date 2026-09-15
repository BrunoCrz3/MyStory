"""Revisor global: fase 4 sobre el manuscrito completo (BUILD_SPEC §7)."""

from __future__ import annotations

import json

from novela.agents.base import JsonAgent
from novela.models import ChapterSummary, GlobalReview, Ledger, StoryBible


class Reviewer(JsonAgent):
    role = "reviewer"

    def run(
        self,
        manuscript: str,
        bible: StoryBible,
        ledger: Ledger,
        summaries: list[ChapterSummary],
    ) -> GlobalReview:
        return self.produce(
            template="reviewer.md",
            schema=GlobalReview,
            role_description="el Revisor global, responsable de la lectura de conjunto",
            manuscript=manuscript,
            bible=json.dumps(bible.model_dump(mode="json"), ensure_ascii=False, indent=2),
            ledger=json.dumps(ledger.model_dump(mode="json"), ensure_ascii=False, indent=2),
            summaries=json.dumps(
                [item.model_dump(mode="json") for item in summaries], ensure_ascii=False, indent=2
            ),
        )
