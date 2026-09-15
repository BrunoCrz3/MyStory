"""Escritor, Reescritor y Parcheador (BUILD_SPEC §7).

Los tres comparten el contexto ensamblado y se diferencian por el rol de modelo
que usan y por lo que se les permite tocar: el Escritor genera, el Reescritor
corrige incidencias bloqueantes y el Parcheador sustituye fragmentos concretos
sin regenerar el capitulo.
"""

from __future__ import annotations

import json

from novela.agents.base import ProseAgent, length_instruction
from novela.context.builder import ChapterContext
from novela.models import ChapterPlan, Issue


def _plan_json(plan: ChapterPlan) -> str:
    return json.dumps(plan.model_dump(mode="json"), ensure_ascii=False, indent=2)


class Writer(ProseAgent):
    role = "writer"

    def run(self, context: ChapterContext, plan: ChapterPlan) -> str:
        return self.generate(
            template="writer.md",
            chapter=plan.number,
            context_layers=context.debug,
            role_description="el Escritor, responsable de la prosa del capítulo",
            context=context.user,
            plan=_plan_json(plan),
            length_instruction=length_instruction(plan.target_length),
            forbidden_openings=context.forbidden_openings,
            forbidden_phrases=context.forbidden_phrases,
            previous_tail=context.previous_tail,
        )


class Rewriter(ProseAgent):
    """Corrige incidencias bloqueantes conservando lo que funciona."""

    role = "rewriter"

    def rewrite(
        self, draft: str, issues: list[Issue], context: ChapterContext, plan: ChapterPlan
    ) -> str:
        return self.generate(
            template="rewriter.md",
            chapter=plan.number,
            context_layers=context.debug,
            role_description="el Reescritor, responsable de corregir incidencias bloqueantes",
            context=context.user,
            draft=draft,
            issues=[item.model_dump(mode="json") for item in issues],
            length_instruction=length_instruction(plan.target_length),
        )

    def patch(
        self, draft: str, issues: list[Issue], context: ChapterContext, plan: ChapterPlan
    ) -> str:
        """Sustituye solo los fragmentos señalados. Nunca regenera el capitulo entero."""
        return self.generate(
            template="patcher.md",
            chapter=plan.number,
            context_layers=context.debug,
            role_description="el Parcheador, responsable de sustituir fragmentos concretos",
            context=context.user,
            draft=draft,
            issues=[item.model_dump(mode="json") for item in issues],
            length_instruction=length_instruction(plan.target_length),
        )
