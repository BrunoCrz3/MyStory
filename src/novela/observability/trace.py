"""Traza append-only, una linea JSON por llamada LLM (BUILD_SPEC §14).

Prohibido registrar la clave de API o el prompt completo: solo su hash y el
desglose de capas de contexto.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path


def prompt_hash(system: str, user: str) -> str:
    digest = hashlib.sha256(f"{system}\x00{user}".encode()).hexdigest()
    return f"sha256:{digest}"


@dataclass
class TraceEvent:
    """Una llamada al modelo. Los campos opcionales solo aplican a OpenRouter."""

    project: str
    role: str
    model: str
    chapter: int | None = None
    attempt: int = 0
    temperature: float = 0.0
    seed: int | None = None
    prompt_hash: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    context_layers: dict[str, int] = field(default_factory=dict)
    json_mode: str | None = None
    generation_id: str | None = None
    effective_provider: str | None = None
    ts: str = ""

    def to_json(self) -> str:
        payload = asdict(self)
        payload["ts"] = self.ts or datetime.now(UTC).isoformat()
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


class TraceWriter:
    """Escritor de `out/<pid>/trace.jsonl`."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: TraceEvent) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(event.to_json() + "\n")

    def read_all(self) -> list[dict[str, object]]:
        if not self.path.is_file():
            return []
        with self.path.open(encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]
