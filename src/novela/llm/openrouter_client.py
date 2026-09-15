"""Cliente OpenRouter (BUILD_SPEC §24).

Implementa el mismo Protocol `LLMClient`: nada fuera de `llm/` cambia al pasar de
Anthropic a OpenRouter. El coste se LEE de la respuesta, nunca se estima con una
tabla de tarifas (§24.5).
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import httpx

from novela.config import OpenRouterCfg
from novela.errors import ProviderError
from novela.llm.base import LLMResponse
from novela.llm.capabilities import Capabilities, JsonMode

ENV_VAR = "OPENROUTER_API_KEY"
TIMEOUT_SECONDS = 120.0
BACKOFF_SECONDS: tuple[float, ...] = (1.0, 2.0, 4.0)
#: Roles cuya prosa exige consistencia de proveedor por encima de disponibilidad (§24.6).
PROSE_ROLES = frozenset({"writer", "rewriter", "patcher", "stylist"})
NO_ENDPOINTS = "no endpoints"


def _api_key() -> str:
    key = os.environ.get(ENV_VAR, "").strip()
    if not key:
        raise ProviderError(
            f"falta la variable de entorno {ENV_VAR}. Copia .env.example a .env y rellena "
            "la clave, o exporta la variable en tu shell."
        )
    return key


class OpenRouterClient:
    """Cliente HTTP con cadena de degradacion JSON y errores accionables."""

    def __init__(
        self,
        cfg: OpenRouterCfg,
        *,
        transport: httpx.BaseTransport | None = None,
        root: Path | None = None,
        api_key: str | None = None,
    ) -> None:
        self.cfg = cfg
        self._key = api_key if api_key is not None else _api_key()
        self._client = httpx.Client(
            timeout=TIMEOUT_SECONDS, transport=transport, base_url=cfg.base_url
        )
        self.capabilities = Capabilities(cfg.base_url, root or Path.cwd(), client=self._client)

    # ---------------- construccion de la peticion ----------------
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._key}",
            "HTTP-Referer": self.cfg.app_referer,
            "X-OpenRouter-Title": self.cfg.app_title,
            "Content-Type": "application/json",
        }

    def provider_block(self, role: str) -> dict[str, Any]:
        block: dict[str, Any] = {
            "require_parameters": self.cfg.require_parameters,
            # Para los roles de prosa, mejor fallar y reintentar que escribir el
            # capitulo 12 con otro proveedor (§24.6).
            "allow_fallbacks": self.cfg.allow_fallbacks if role in PROSE_ROLES else True,
            "data_collection": self.cfg.data_collection,
        }
        if self.cfg.provider_order:
            block["order"] = list(self.cfg.provider_order)
        return block

    def build_body(
        self,
        *,
        system: str,
        user: str,
        model: str,
        temperature: float,
        max_tokens: int,
        seed: int | None,
        role: str,
        json_schema: dict[str, object] | None,
        mode: JsonMode,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "provider": self.provider_block(role),
        }
        # `seed` solo se envia si el modelo lo admite; no se asume determinismo (§24.7).
        if seed is not None and self.capabilities.supports(model, "seed"):
            body["seed"] = seed
        if json_schema is None or mode is JsonMode.PROMPT:
            return body
        if mode is JsonMode.SCHEMA:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": str(json_schema.get("title", "output")).lower(),
                    "strict": True,
                    "schema": json_schema,
                },
            }
        else:
            body["response_format"] = {"type": "json_object"}
        return body

    # ---------------- llamada ----------------
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
        mode = self.capabilities.json_mode_for(model) if json_schema else JsonMode.PROMPT
        attempted: list[JsonMode] = []

        while True:
            attempted.append(mode)
            body = self.build_body(
                system=system,
                user=user,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                seed=seed,
                role=role,
                json_schema=json_schema,
                mode=mode,
            )
            try:
                return self._post(body, mode)
            except _Degrade as signal:
                if mode is JsonMode.PROMPT:
                    raise _no_endpoints_error(model, role, signal.detail) from signal
                mode = self.capabilities.degrade(mode)

    def _post(self, body: dict[str, Any], mode: JsonMode) -> LLMResponse:
        last: Exception | None = None
        for delay in (*BACKOFF_SECONDS, None):
            started = time.monotonic()
            try:
                response = self._client.post("/chat/completions", json=body, headers=self.headers())
            except httpx.HTTPError as error:
                last = error
                if delay is None:
                    break
                time.sleep(delay)
                continue

            if response.status_code == 429:
                if delay is None:
                    break
                time.sleep(delay)
                continue
            if response.status_code >= 500:
                last = ProviderError(f"error {response.status_code} del proveedor de destino")
                if delay is None:
                    break
                time.sleep(delay)
                continue
            _raise_for_status(response)
            return _to_response(response.json(), body["model"], started, mode)

        raise ProviderError(f"OpenRouter no responde tras varios intentos: {last}")


class _Degrade(Exception):
    """Señal interna: el nivel de forzado de JSON pedido no tiene endpoint disponible."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code < 400:
        return
    detail = _error_detail(response)
    if response.status_code == 401:
        raise ProviderError(
            f"OpenRouter ha rechazado la autenticación (401). Revisa la variable {ENV_VAR}: "
            f"ausente o inválida. Detalle: {detail}"
        )
    if response.status_code == 402:
        raise ProviderError(
            "OpenRouter informa de créditos insuficientes (402). El proyecto queda PAUSED sin "
            f"perder trabajo: recarga la cuenta y reanuda con `novela write`. Detalle: {detail}"
        )
    if response.status_code == 404 and NO_ENDPOINTS in detail.lower():
        raise _Degrade(detail)
    raise ProviderError(f"OpenRouter ha devuelto {response.status_code}: {detail}")


def _error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:300]
    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("message", error))
    return str(error or payload)[:300]


def _no_endpoints_error(model: str, role: str, detail: str) -> ProviderError:
    return ProviderError(
        f"OpenRouter no encuentra ningún proveedor para '{model}' (rol '{role}') con los "
        "parámetros pedidos, ni siquiera tras degradar a modo prompt. Opciones: pon "
        "`llm.openrouter.require_parameters: false`, o cambia el modelo de ese rol en "
        f"`llm.models.{role}.name`. Detalle del proveedor: {detail}"
    )


def _to_response(
    payload: dict[str, Any], model: str, started: float, mode: JsonMode
) -> LLMResponse:
    choices = payload.get("choices") or []
    # Respuesta vacia: se trata como fallo de esquema y lo reintenta agents/base (§24.8).
    text = str(choices[0].get("message", {}).get("content") or "") if choices else ""
    usage = payload.get("usage") or {}
    return LLMResponse(
        text=text,
        input_tokens=int(usage.get("prompt_tokens", 0) or 0),
        output_tokens=int(usage.get("completion_tokens", 0) or 0),
        model=str(payload.get("model", model)),
        latency_ms=int((time.monotonic() - started) * 1000),
        # El coste se lee, nunca se estima (§24.5).
        cost_usd=float(usage["cost"]) if "cost" in usage else None,
        generation_id=str(payload.get("id")) if payload.get("id") else None,
        effective_provider=str(payload.get("provider")) if payload.get("provider") else None,
        json_mode=mode.value,
    )
