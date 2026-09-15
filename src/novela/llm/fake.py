"""Proveedor determinista y offline (BUILD_SPEC §6.2).

Sin este componente no hay tests reproducibles: la reproducibilidad de la suite
depende EXCLUSIVAMENTE del `FakeLLM`, nunca de un proveedor real (§24.7).

Resolucion de fixtures. La clave de llamada es `<rol>` o `<rol>_ch<n>` para los
roles que trabajan capitulo a capitulo. Esa clave se traduce al fichero de
`fixtures/llm/` segun `FIXTURE_ALIASES`: el Reescritor y el Estilista leen la
misma fixture que el Escritor del mismo capitulo, porque su contrato es devolver
el texto canonico de ese capitulo.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from novela.errors import FixtureMissing, ProviderError
from novela.llm.base import LLMResponse

CHAPTER_ROLES = frozenset({"writer", "rewriter", "patcher", "stylist", "archivist", "judge"})

#: Modos de fallo programables para ejercitar los bucles del orquestador.
FAILURE_MODES = frozenset({"invalid_json", "too_long", "too_short", "duplicate", "empty"})

INVALID_JSON_PAYLOAD = 'Claro, aqui tienes el resultado:\n{"facts": [ , ] "summary" }'


def fixture_key(call_key: str) -> str:
    """Traduce la clave de llamada al nombre del fichero de fixture."""
    if call_key.startswith(("rewriter_ch", "stylist_ch", "patcher_ch")):
        return "writer_ch" + call_key.rsplit("_ch", 1)[1]
    if call_key.startswith("judge"):
        return "judge_clean"
    return call_key


def call_key(role: str, chapter: int | None) -> str:
    if role in CHAPTER_ROLES and chapter is not None:
        return f"{role}_ch{chapter}"
    return role


class FakeLLM:
    """Cliente LLM que resuelve cada llamada leyendo una fixture del disco."""

    def __init__(
        self,
        fixtures_dir: Path,
        *,
        fail_plan: dict[str, list[str]] | None = None,
    ) -> None:
        self.fixtures_dir = Path(fixtures_dir)
        self.fail_plan: dict[str, list[str]] = {
            key: list(modes) for key, modes in (fail_plan or {}).items()
        }
        self._validate_fail_plan(self.fail_plan.values())
        self.calls: list[tuple[str, str]] = []

    @staticmethod
    def _validate_fail_plan(plans: Iterable[list[str]]) -> None:
        for modes in plans:
            unknown = set(modes) - FAILURE_MODES
            if unknown:
                raise ProviderError(
                    f"modos de fallo desconocidos en fail_plan: {sorted(unknown)}. "
                    f"Admitidos: {sorted(FAILURE_MODES)}"
                )

    def _load(self, key: str) -> dict[str, Any]:
        path = self.fixtures_dir / f"{fixture_key(key)}.json"
        if not path.is_file():
            raise FixtureMissing(key, str(path))
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ProviderError(f"la fixture '{path}' debe contener un objeto JSON")
        return payload

    def _render(self, payload: dict[str, Any]) -> str:
        output_type = payload.get("output_type")
        if output_type == "text":
            return str(payload["text"])
        if output_type == "json":
            return json.dumps(payload["json"], ensure_ascii=False, indent=2)
        raise ProviderError(
            f"la fixture declara output_type='{output_type}'; se esperaba 'text' o 'json'"
        )

    def _apply_failure(self, mode: str, key: str, text: str) -> str:
        if mode == "invalid_json":
            return INVALID_JSON_PAYLOAD
        if mode == "empty":
            return ""
        if mode == "too_long":
            return text.rstrip("\n") + "\nUna línea sobrante que rompe la longitud exigida.\n"
        if mode == "too_short":
            lines = [line for line in text.splitlines() if line.strip()]
            return "\n".join(lines[:-1]) + "\n" if len(lines) > 1 else ""
        # duplicate: devuelve el texto del capitulo 1 para disparar la repeticion.
        source = self._load("writer_ch1")
        if key.startswith("writer") or key.startswith("rewriter") or key.startswith("stylist"):
            return self._render(source)
        return text

    def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        temperature: float,
        max_tokens: int,
        seed: int | None = None,
        role: str = "unknown",
        chapter: int | None = None,
        json_schema: dict[str, object] | None = None,
    ) -> LLMResponse:
        key = call_key(role, chapter)
        self.calls.append((key, model))
        text = self._render(self._load(key))

        pending = self.fail_plan.get(key)
        if pending:
            text = self._apply_failure(pending.pop(0), key, text)

        # Metricas deterministas: ni red, ni reloj, ni aleatoriedad.
        return LLMResponse(
            text=text,
            input_tokens=len(system) // 4 + len(user) // 4,
            output_tokens=len(text) // 4,
            model=model,
            latency_ms=0,
            cost_usd=0.0,
            json_mode="fake",
        )
