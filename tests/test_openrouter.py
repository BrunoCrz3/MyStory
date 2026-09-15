"""T-14 y T-15: construcción de la petición y degradación por capacidad.

Ninguna llamada real: todo pasa por `httpx.MockTransport`.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from novela.config import OpenRouterCfg
from novela.errors import ProviderError
from novela.llm.capabilities import Capabilities, JsonMode
from novela.llm.openrouter_client import OpenRouterClient
from novela.models import StoryBible

MODEL = "anthropic/claude-sonnet-4.5"


@pytest.fixture
def cfg() -> OpenRouterCfg:
    return OpenRouterCfg(
        base_url="https://openrouter.ai/api/v1",
        app_title="novela-agent",
        app_referer="https://example.invalid/novela-agent",
        require_parameters=True,
        allow_fallbacks=False,
        data_collection="deny",
        provider_order=["anthropic"],
    )


def _models_payload(parameters: list[str]) -> dict[str, object]:
    return {"data": [{"id": MODEL, "supported_parameters": parameters}]}


def _completion_payload() -> dict[str, object]:
    return {
        "id": "gen-123",
        "model": MODEL,
        "provider": "Anthropic",
        "choices": [{"message": {"role": "assistant", "content": '{"ok": true}'}}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 40, "cost": 0.0031},
    }


def _client(
    cfg: OpenRouterCfg,
    tmp_path: Path,
    handler: object,
    parameters: list[str] | None = None,
) -> tuple[OpenRouterClient, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def route(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json=_models_payload(parameters or []))
        return handler(request)  # type: ignore[operator]

    client = OpenRouterClient(
        cfg,
        transport=httpx.MockTransport(route),
        root=tmp_path,
        api_key="CLAVE_DE_PRUEBA",
    )
    return client, seen


# ---------------------------------------------------------------- T-14
def test_request_body_and_headers_are_well_formed(cfg: OpenRouterCfg, tmp_path: Path) -> None:
    client, seen = _client(
        cfg,
        tmp_path,
        lambda request: httpx.Response(200, json=_completion_payload()),
        parameters=["structured_outputs", "response_format", "seed"],
    )
    schema = StoryBible.model_json_schema()
    response = client.complete(
        system="rol",
        user="tarea",
        model=MODEL,
        temperature=0.9,
        max_tokens=4000,
        seed=20260915,
        role="architect",
        json_schema=schema,
    )

    completion = [r for r in seen if r.url.path.endswith("/chat/completions")][-1]
    body = json.loads(completion.content)

    # Modelo con espacio de nombres y mensajes con rol system explícito.
    assert body["model"] == MODEL
    assert [message["role"] for message in body["messages"]] == ["system", "user"]
    # response_format con json_schema estricto.
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["schema"]["title"] == "StoryBible"
    # Bloque provider con las garantías de §24.2 y §24.6.
    assert body["provider"] == {
        "require_parameters": True,
        "allow_fallbacks": True,  # 'architect' no es rol de prosa
        "data_collection": "deny",
        "order": ["anthropic"],
    }
    assert body["seed"] == 20260915
    # Cabeceras de atribución, y la clave jamás en el cuerpo.
    assert completion.headers["HTTP-Referer"] == cfg.app_referer
    assert completion.headers["X-OpenRouter-Title"] == cfg.app_title
    assert completion.headers["Authorization"] == "Bearer CLAVE_DE_PRUEBA"
    assert "CLAVE_DE_PRUEBA" not in completion.content.decode()
    # El coste se LEE de la respuesta, no se estima.
    assert response.cost_usd == 0.0031
    assert response.generation_id == "gen-123"
    assert response.effective_provider == "Anthropic"


def test_prose_roles_never_allow_fallbacks(cfg: OpenRouterCfg, tmp_path: Path) -> None:
    client, seen = _client(
        cfg, tmp_path, lambda request: httpx.Response(200, json=_completion_payload())
    )
    client.complete(
        system="s", user="u", model=MODEL, temperature=0.9, max_tokens=100, role="writer"
    )
    body = json.loads([r for r in seen if "completions" in r.url.path][-1].content)
    assert body["provider"]["allow_fallbacks"] is False


def test_seed_is_omitted_when_the_model_does_not_support_it(
    cfg: OpenRouterCfg, tmp_path: Path
) -> None:
    client, seen = _client(
        cfg,
        tmp_path,
        lambda request: httpx.Response(200, json=_completion_payload()),
        parameters=["response_format"],
    )
    client.complete(
        system="s",
        user="u",
        model=MODEL,
        temperature=0.5,
        max_tokens=100,
        seed=42,
        role="archivist",
    )
    body = json.loads([r for r in seen if "completions" in r.url.path][-1].content)
    assert "seed" not in body


# ---------------------------------------------------------------- T-15
def test_degradation_walks_the_three_levels(cfg: OpenRouterCfg, tmp_path: Path) -> None:
    modes: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        fmt = body.get("response_format")
        modes.append(fmt["type"] if fmt else "prompt")
        if fmt is not None:
            return httpx.Response(
                404, json={"error": {"message": "No endpoints found that support json_schema"}}
            )
        return httpx.Response(200, json=_completion_payload())

    client, _ = _client(
        cfg, tmp_path, handler, parameters=["structured_outputs", "response_format"]
    )
    response = client.complete(
        system="s",
        user="u",
        model=MODEL,
        temperature=0.1,
        max_tokens=100,
        role="archivist",
        json_schema={"title": "X", "type": "object"},
    )
    assert modes == ["json_schema", "json_object", "prompt"]
    assert response.json_mode == JsonMode.PROMPT.value


def test_no_endpoints_at_the_last_level_is_an_actionable_provider_error(
    cfg: OpenRouterCfg, tmp_path: Path
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={"error": {"message": "No endpoints found that support the requested parameters"}},
        )

    client, _ = _client(cfg, tmp_path, handler, parameters=["structured_outputs"])
    with pytest.raises(ProviderError) as error:
        client.complete(
            system="s",
            user="u",
            model=MODEL,
            temperature=0.1,
            max_tokens=100,
            role="judge",
            json_schema={"title": "X", "type": "object"},
        )
    message = str(error.value)
    assert MODEL in message
    assert "require_parameters" in message
    assert "llm.models.judge.name" in message


@pytest.mark.parametrize(
    ("status", "needle"),
    [(401, "OPENROUTER_API_KEY"), (402, "créditos insuficientes")],
)
def test_auth_and_credit_errors_are_explicit(
    cfg: OpenRouterCfg, tmp_path: Path, status: int, needle: str
) -> None:
    client, _ = _client(
        cfg, tmp_path, lambda request: httpx.Response(status, json={"error": {"message": "nope"}})
    )
    with pytest.raises(ProviderError, match=needle):
        client.complete(
            system="s", user="u", model=MODEL, temperature=0.1, max_tokens=10, role="judge"
        )


def test_empty_response_is_treated_as_a_schema_failure(cfg: OpenRouterCfg, tmp_path: Path) -> None:
    client, _ = _client(
        cfg, tmp_path, lambda request: httpx.Response(200, json={"id": "g", "choices": []})
    )
    response = client.complete(
        system="s", user="u", model=MODEL, temperature=0.1, max_tokens=10, role="judge"
    )
    # Texto vacío: agents/base lo reintenta dentro de max_schema_retries.
    assert response.text == ""


# ---------------------------------------------------------------- capacidades
def test_capabilities_cache_survives_and_reports_unknown(tmp_path: Path) -> None:
    calls = {"n": 0}

    def route(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json=_models_payload(["structured_outputs"]))

    http = httpx.Client(transport=httpx.MockTransport(route))
    caps = Capabilities("https://openrouter.ai/api/v1", tmp_path, client=http)
    assert caps.supports(MODEL, "structured_outputs") is True
    assert caps.supports(MODEL, "seed") is False
    assert caps.supports("otro/modelo", "seed") is None
    assert caps.json_mode_for(MODEL) is JsonMode.SCHEMA
    assert calls["n"] == 1  # la segunda consulta sale de la caché en memoria

    fresh = Capabilities("https://openrouter.ai/api/v1", tmp_path, client=http)
    assert fresh.supports(MODEL, "structured_outputs") is True
    assert calls["n"] == 1  # y la tercera, de la caché en disco


def test_unknown_model_falls_back_to_prompt_mode(tmp_path: Path) -> None:
    http = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(500, text="boom"))
    )
    caps = Capabilities("https://openrouter.ai/api/v1", tmp_path, client=http)
    assert caps.supports(MODEL, "structured_outputs") is None
    assert caps.json_mode_for(MODEL) is JsonMode.PROMPT
    assert caps.degrade(JsonMode.SCHEMA) is JsonMode.OBJECT
    assert caps.degrade(JsonMode.OBJECT) is JsonMode.PROMPT
