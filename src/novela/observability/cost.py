"""Agregacion de coste por rol y capitulo (BUILD_SPEC §14, §24.5).

Con proveedor Anthropic directo el coste se calcula con la tabla de tarifas de
este modulo. Con OpenRouter el coste lo devuelve la propia respuesta y NUNCA se
estima: `novela cost` muestra coste observado, no estimado.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

# USD por millon de tokens (entrada, salida). Solo se usa con el proveedor
# Anthropic directo, que no informa del coste en la respuesta.
ANTHROPIC_RATES_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-opus-4": (15.0, 75.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}
FALLBACK_RATE_PER_MTOK = (3.0, 15.0)


def anthropic_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rate_in, rate_out = ANTHROPIC_RATES_PER_MTOK.get(model, FALLBACK_RATE_PER_MTOK)
    return (input_tokens * rate_in + output_tokens * rate_out) / 1_000_000


@dataclass(frozen=True)
class CostEntry:
    role: str
    chapter: int | None
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class CostTracker:
    """Acumula el coste observado de un proyecto y lo persiste en `cost.json`."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.entries: list[CostEntry] = []

    def record(self, entry: CostEntry) -> None:
        self.entries.append(entry)

    def total(self) -> float:
        return sum(entry.cost_usd for entry in self.entries)

    def by_role(self) -> dict[str, float]:
        totals: dict[str, float] = defaultdict(float)
        for entry in self.entries:
            totals[entry.role] += entry.cost_usd
        return dict(totals)

    def by_chapter(self) -> dict[str, float]:
        totals: dict[str, float] = defaultdict(float)
        for entry in self.entries:
            key = "sin_capitulo" if entry.chapter is None else f"ch_{entry.chapter:02d}"
            totals[key] += entry.cost_usd
        return dict(totals)

    def tokens(self) -> tuple[int, int]:
        return (
            sum(entry.input_tokens for entry in self.entries),
            sum(entry.output_tokens for entry in self.entries),
        )

    def as_dict(self) -> dict[str, object]:
        input_tokens, output_tokens = self.tokens()
        return {
            "total_usd": round(self.total(), 6),
            "calls": len(self.entries),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "by_role": {role: round(value, 6) for role, value in sorted(self.by_role().items())},
            "by_chapter": {
                key: round(value, 6) for key, value in sorted(self.by_chapter().items())
            },
        }

    def flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.as_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    @classmethod
    def load_total(cls, path: Path) -> float:
        if not path.is_file():
            return 0.0
        data = json.loads(path.read_text(encoding="utf-8"))
        return float(data.get("total_usd", 0.0))
