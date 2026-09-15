"""Estilista: pulido final sin alterar hechos ni longitud (BUILD_SPEC §7)."""

from __future__ import annotations

from novela.agents.base import ProseAgent, length_instruction
from novela.context.builder import ChapterContext
from novela.models import ChapterPlan


class Stylist(ProseAgent):
    role = "stylist"

    def run(self, draft: str, context: ChapterContext, plan: ChapterPlan) -> str:
        return self.generate(
            template="stylist.md",
            chapter=plan.number,
            context_layers=context.debug,
            role_description="el Estilista, responsable del pulido final de la prosa",
            context=context.user,
            draft=draft,
            length_instruction=length_instruction(plan.target_length),
            forbidden_phrases=context.forbidden_phrases,
        )
