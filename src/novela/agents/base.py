"""Ciclo comun de los agentes (BUILD_SPEC §6.5, §7.2).

    renderizar prompt (Jinja2)
    -> llamar al LLM
    -> extraer JSON (tolerando ```json ... ``` y preambulos)
    -> validar contra el modelo Pydantic
    -> si falla: reintentar inyectando el error de validacion literal
    -> si agota reintentos: SchemaRetryExhausted

Nunca se parsea prosa con expresiones regulares (§18): se parsea JSON y se valida
con Pydantic.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, ValidationError

from novela.config import Config
from novela.errors import SchemaRetryExhausted
from novela.llm.router import Router
from novela.models import LengthSpec
from novela.observability.cost import CostEntry, CostTracker, anthropic_cost
from novela.observability.trace import TraceEvent, TraceWriter, prompt_hash

ModelT = TypeVar("ModelT", bound=BaseModel)


def length_instruction(spec: LengthSpec) -> str:
    """Unico punto del sistema que traduce configuracion de tamaño a lenguaje natural."""
    if spec.unit == "lines":
        return (
            f"Escribe EXACTAMENTE {spec.target} líneas de prosa. "
            "Cada línea es una frase completa terminada en salto de línea. "
            "No uses títulos, viñetas, numeración ni líneas en blanco intermedias."
        )
    low, high = spec.bounds()
    return f"Escribe entre {low} y {high} palabras de prosa continua en párrafos."


def extract_json(text: str) -> str:
    """Localiza el primer objeto JSON balanceado. No asume que la respuesta empieza por '{'.

    Los modelos de razonamiento anteponen texto al JSON y los modelos de chat lo
    envuelven en vallas de codigo: ambos casos se toleran aqui (§24.4).
    """
    depth = 0
    start = -1
    in_string = False
    escaped = False
    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                return text[start : index + 1]
    raise ValueError("la respuesta no contiene ningún objeto JSON balanceado")


@dataclass
class AgentContext:
    """Todo lo que un agente necesita del entorno, ya resuelto."""

    config: Config
    router: Router
    trace: TraceWriter
    cost: CostTracker
    project_id: str
    prompts_dir: Path

    def environment(self) -> Environment:
        return Environment(
            loader=FileSystemLoader(self.prompts_dir),
            undefined=StrictUndefined,
            autoescape=False,
            keep_trailing_newline=True,
        )

    def render(self, template: str, **variables: object) -> str:
        novel = self.config.novel
        common = {
            "language": self.config.project.language,
            "subgenre": novel.subgenre,
            "tone": novel.tone,
            "pov": novel.pov,
            "tense": novel.tense,
            "structure": novel.structure,
            "hardness": novel.hardness,
            "forbidden": novel.forbidden,
        }
        return self.environment().get_template(template).render(**common, **variables)


class BaseAgent:
    """Mecanica compartida: llamada al modelo, traza y coste."""

    role: str = "unknown"

    def __init__(self, context: AgentContext) -> None:
        self.context = context

    def _call(
        self,
        *,
        system: str,
        user: str,
        chapter: int | None,
        attempt: int,
        context_layers: dict[str, int] | None = None,
    ) -> str:
        model = self.context.config.model_for(self.role)
        response = self.context.router.complete(
            role=self.role, system=system, user=user, chapter=chapter
        )
        cost = (
            response.cost_usd
            if response.cost_usd is not None
            else anthropic_cost(response.model, response.input_tokens, response.output_tokens)
        )
        self.context.cost.record(
            CostEntry(
                role=self.role,
                chapter=chapter,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost_usd=cost,
            )
        )
        self.context.trace.write(
            TraceEvent(
                project=self.context.project_id,
                role=self.role,
                model=response.model,
                chapter=chapter,
                attempt=attempt,
                temperature=model.temperature,
                seed=self.context.config.project.seed,
                prompt_hash=prompt_hash(system, user),
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost_usd=cost,
                latency_ms=response.latency_ms,
                context_layers=context_layers or {},
                json_mode=response.json_mode,
                generation_id=response.generation_id,
                effective_provider=response.effective_provider,
            )
        )
        return response.text


class ProseAgent(BaseAgent):
    """Agente cuya salida es prosa: no hay esquema que validar, solo texto."""

    def generate(
        self,
        *,
        template: str,
        chapter: int | None = None,
        context_layers: dict[str, int] | None = None,
        **variables: object,
    ) -> str:
        rendered = self.context.render(template, **variables)
        system, user = split_prompt(rendered)
        return self._call(
            system=system,
            user=user,
            chapter=chapter,
            attempt=0,
            context_layers=context_layers,
        ).strip("\n")


class JsonAgent(BaseAgent):
    """Agente cuya salida es JSON validado contra un modelo Pydantic."""

    def produce(
        self,
        *,
        template: str,
        schema: type[ModelT],
        chapter: int | None = None,
        context_layers: dict[str, int] | None = None,
        **variables: object,
    ) -> ModelT:
        rendered = self.context.render(template, **variables)
        system, user = split_prompt(rendered)
        retries = self.context.config.limits.max_schema_retries
        last_error = ""

        for attempt in range(retries):
            payload = self._call(
                system=system,
                user=user if attempt == 0 else f"{user}\n\n{repair_note(last_error)}",
                chapter=chapter,
                attempt=attempt,
                context_layers=context_layers,
            )
            try:
                return schema.model_validate_json(extract_json(payload))
            except (ValueError, ValidationError) as error:
                last_error = str(error)

        raise SchemaRetryExhausted(self.role, retries, last_error)


def repair_note(error: str) -> str:
    """Inyecta el error de validacion literal para que el modelo corrija ese fallo concreto."""
    return (
        "## Corrección obligatoria\n\n"
        "Tu respuesta anterior no ha superado la validación del esquema. Este es el error "
        "literal del validador:\n\n"
        f"```\n{error[:2000]}\n```\n\n"
        "Devuelve de nuevo el objeto JSON completo, corrigiendo exactamente ese fallo y sin "
        "cambiar nada más. No expliques el cambio."
    )


#: Separador entre el bloque de sistema y el de usuario dentro de una plantilla.
PROMPT_SPLIT = "\n## Tarea\n"


def split_prompt(rendered: str) -> tuple[str, str]:
    """Divide la plantilla en `system` (rol y restricciones) y `user` (la tarea concreta)."""
    if PROMPT_SPLIT in rendered:
        system, task = rendered.split(PROMPT_SPLIT, 1)
        return system.strip(), (PROMPT_SPLIT + task).strip()
    return rendered.strip(), "Ejecuta la tarea descrita."
