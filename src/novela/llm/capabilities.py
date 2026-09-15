"""Capacidades por modelo y cadena de degradacion JSON (BUILD_SPEC §24.4).

Consulta `GET {base_url}/models`, cachea `supported_parameters` en disco con TTL
de 24 h y expone `supports(model, parameter) -> bool | None`, donde `None`
significa "desconocido".

Regla dura: la validacion Pydantic se aplica igual en los tres niveles. La
degradacion afecta a COMO se pide el JSON, nunca a como se comprueba.
"""

from __future__ import annotations

import json
import time
from enum import StrEnum
from pathlib import Path

import httpx

CACHE_TTL_SECONDS = 24 * 60 * 60
CACHE_FILENAME = "openrouter_models.json"


class JsonMode(StrEnum):
    """Los tres niveles de la cadena de degradacion de §24.4."""

    SCHEMA = "json_schema"
    OBJECT = "json_object"
    PROMPT = "prompt"


def cache_path(root: Path) -> Path:
    return root / ".cache" / CACHE_FILENAME


class Capabilities:
    """Cache de `supported_parameters` por modelo."""

    def __init__(self, base_url: str, root: Path, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.path = cache_path(root)
        self._client = client
        self._data: dict[str, list[str]] | None = None

    def _load_cache(self) -> dict[str, list[str]] | None:
        if not self.path.is_file():
            return None
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if time.time() - float(payload.get("fetched_at", 0)) > CACHE_TTL_SECONDS:
            return None
        models = payload.get("models")
        return models if isinstance(models, dict) else None

    def _store_cache(self, models: dict[str, list[str]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"fetched_at": time.time(), "models": models}, ensure_ascii=False),
            encoding="utf-8",
        )

    def refresh(self) -> dict[str, list[str]]:
        client = self._client or httpx.Client(timeout=30.0)
        try:
            response = client.get(f"{self.base_url}/models")
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            # Sin red la degradacion sigue funcionando: `supports` devuelve None.
            return {}
        models = {
            str(item.get("id")): [str(param) for param in item.get("supported_parameters", [])]
            for item in payload.get("data", [])
            if item.get("id")
        }
        if models:
            self._store_cache(models)
        return models

    def _models(self) -> dict[str, list[str]]:
        if self._data is None:
            self._data = self._load_cache() or self.refresh()
        return self._data

    def supports(self, model: str, parameter: str) -> bool | None:
        models = self._models()
        if model not in models:
            return None
        return parameter in models[model]

    def json_mode_for(self, model: str) -> JsonMode:
        """Elige el nivel mas alto que el modelo declara soportar."""
        if self.supports(model, "structured_outputs"):
            return JsonMode.SCHEMA
        if self.supports(model, "response_format"):
            return JsonMode.OBJECT
        return JsonMode.PROMPT

    def degrade(self, mode: JsonMode) -> JsonMode:
        """Siguiente nivel de la cadena tras un rechazo del proveedor."""
        if mode is JsonMode.SCHEMA:
            return JsonMode.OBJECT
        return JsonMode.PROMPT
