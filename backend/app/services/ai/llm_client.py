"""Thin, provider-agnostic wrapper around the LLM used for generation.

Supports Google Gemini (default) and Anthropic Claude, selected via
AI_LLM_PROVIDER. The rest of the codebase depends only on the functions
below (``complete`` / ``complete_json`` / ``complete_with_tools``), never on
a provider SDK directly, so switching providers -- or adding a third one --
never touches the agents. Clients are constructed lazily so importing this
module never fails when no API key is configured yet; callers get a clear
AIUnavailableError only when they actually try to generate something.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.core.config import settings


class AIUnavailableError(RuntimeError):
    """Raised when generation is requested but no LLM provider is configured."""


@dataclass
class LLMMessage:
    role: str  # "user" | "assistant"
    content: str


_anthropic_client = None
_gemini_client = None


def is_configured() -> bool:
    if settings.ai_llm_provider == "gemini":
        return bool(settings.gemini_api_key)
    return bool(settings.anthropic_api_key)


def _require_configured() -> None:
    if not is_configured():
        raise AIUnavailableError(
            f"No API key configured for provider '{settings.ai_llm_provider}'. "
            "Set GEMINI_API_KEY or ANTHROPIC_API_KEY (and AI_LLM_PROVIDER) in backend/.env."
        )


# --- Anthropic ---------------------------------------------------------------


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is not None:
        return _anthropic_client
    import anthropic

    _anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


def _anthropic_complete(system: str, messages: list[LLMMessage], max_tokens: int) -> str:
    client = _get_anthropic_client()
    response = client.messages.create(
        model=settings.ai_model_name,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": m.role, "content": m.content} for m in messages],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def _anthropic_complete_with_tools(system: str, messages: list[LLMMessage], tools: list[dict], max_tokens: int) -> dict:
    client = _get_anthropic_client()
    response = client.messages.create(
        model=settings.ai_model_name,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": m.role, "content": m.content} for m in messages],
        tools=tools,
    )
    text_parts = [block.text for block in response.content if block.type == "text"]
    tool_calls = [{"name": b.name, "input": b.input} for b in response.content if b.type == "tool_use"]
    return {"text": "\n".join(text_parts).strip(), "tool_calls": tool_calls}


# --- Gemini -------------------------------------------------------------------


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client
    from google import genai

    _gemini_client = genai.Client(api_key=settings.gemini_api_key)
    return _gemini_client


def _sanitize_schema_for_gemini(schema: dict) -> dict:
    """Gemini's function-calling Schema (proto-based) doesn't support JSON
    Schema union types (``"type": ["string", "null"]``) or ``None`` inside
    ``enum`` lists the way our Anthropic-style tool schemas use for optional
    fields. Strip both, recursively, without mutating the input."""
    result = dict(schema)

    schema_type = result.get("type")
    if isinstance(schema_type, list):
        non_null = [t for t in schema_type if t != "null"]
        result["type"] = non_null[0] if non_null else "string"

    if isinstance(result.get("enum"), list):
        result["enum"] = [v for v in result["enum"] if v is not None]

    if isinstance(result.get("properties"), dict):
        result["properties"] = {key: _sanitize_schema_for_gemini(value) for key, value in result["properties"].items()}

    return result


def _generate_with_thinking_fallback(client, *, contents, base_config_kwargs: dict):
    """Calls generate_content with thinking disabled (see rationale below),
    but falls back to a call without thinking_config if the model/API
    rejects that parameter combination.

    Disabling "thinking" is desirable for our tasks (grounded RAG answers,
    NL-to-SQL, JSON classification, tool-call extraction, row summaries --
    all direct extraction/generation, not multi-step reasoning): newer
    Gemini models otherwise spend part of max_output_tokens on hidden
    "thinking" tokens by default, which was silently truncating visible
    output well short of the requested limit.

    However, `thinking_config` support/behavior is inconsistent across
    Gemini model versions and API surface areas (see e.g.
    https://github.com/googleapis/python-genai/issues/706 and /782), and an
    alias like "gemini-flash-latest" can resolve to a different underlying
    model over time -- one that may reject the parameter outright with a
    generic 400 INVALID_ARGUMENT. Since silently crashing an otherwise
    working feature over a token-budget optimization is worse than
    occasionally getting a truncated answer, we retry once without it
    rather than letting the error propagate.
    """
    from google.genai import errors, types

    try:
        config = types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_budget=0), **base_config_kwargs)
        return client.models.generate_content(model=settings.ai_model_name, contents=contents, config=config)
    except errors.ClientError:
        config = types.GenerateContentConfig(**base_config_kwargs)
        return client.models.generate_content(model=settings.ai_model_name, contents=contents, config=config)


def _gemini_complete(system: str, messages: list[LLMMessage], max_tokens: int, json_mode: bool = False) -> str:
    from google.genai import types

    client = _get_gemini_client()
    role_map = {"user": "user", "assistant": "model"}
    contents = [
        types.Content(role=role_map.get(m.role, "user"), parts=[types.Part.from_text(text=m.content)])
        for m in messages
    ]
    response = _generate_with_thinking_fallback(
        client,
        contents=contents,
        base_config_kwargs={
            "system_instruction": system,
            "max_output_tokens": max_tokens,
            "response_mime_type": "application/json" if json_mode else None,
        },
    )
    return response.text or ""


def _gemini_complete_with_tools(system: str, messages: list[LLMMessage], tools: list[dict], max_tokens: int) -> dict:
    from google.genai import types

    client = _get_gemini_client()
    role_map = {"user": "user", "assistant": "model"}
    contents = [
        types.Content(role=role_map.get(m.role, "user"), parts=[types.Part.from_text(text=m.content)])
        for m in messages
    ]
    function_declarations = [
        types.FunctionDeclaration(
            name=tool["name"],
            description=tool["description"],
            parameters=_sanitize_schema_for_gemini(tool["input_schema"]),
        )
        for tool in tools
    ]
    response = _generate_with_thinking_fallback(
        client,
        contents=contents,
        base_config_kwargs={
            "system_instruction": system,
            "max_output_tokens": max_tokens,
            "tools": [types.Tool(function_declarations=function_declarations)] if function_declarations else None,
        },
    )

    text_parts: list[str] = []
    tool_calls: list[dict] = []
    candidates = response.candidates or []
    parts = candidates[0].content.parts if candidates and candidates[0].content else []
    for part in parts or []:
        if getattr(part, "function_call", None) is not None:
            fc = part.function_call
            tool_calls.append({"name": fc.name, "input": dict(fc.args) if fc.args else {}})
        elif getattr(part, "text", None):
            text_parts.append(part.text)

    return {"text": "\n".join(text_parts).strip(), "tool_calls": tool_calls}


# --- Public, provider-agnostic API --------------------------------------------


async def complete(system: str, messages: list[LLMMessage], max_tokens: int | None = None) -> str:
    """Single-turn (or multi-turn) text completion. Raises AIUnavailableError if unconfigured."""
    import anyio

    _require_configured()
    effective_max_tokens = max_tokens or settings.ai_max_output_tokens

    def _call() -> str:
        if settings.ai_llm_provider == "gemini":
            return _gemini_complete(system, messages, effective_max_tokens)
        return _anthropic_complete(system, messages, effective_max_tokens)

    return await anyio.to_thread.run_sync(_call)


async def complete_with_tools(system: str, messages: list[LLMMessage], tools: list[dict], max_tokens: int | None = None) -> dict:
    """Multi-turn call that may result in a tool call. `messages` is the
    conversation so far (prior turns, if any, then the latest user message)
    so the model can resolve follow-ups like "its a casual leave" answering
    an earlier clarifying question. Returns
    {"text": str, "tool_calls": [{"name": str, "input": dict}]}."""
    import anyio

    _require_configured()
    effective_max_tokens = max_tokens or settings.ai_max_output_tokens

    def _call() -> dict:
        if settings.ai_llm_provider == "gemini":
            return _gemini_complete_with_tools(system, messages, tools, effective_max_tokens)
        return _anthropic_complete_with_tools(system, messages, tools, effective_max_tokens)

    return await anyio.to_thread.run_sync(_call)


async def complete_json(system: str, user_prompt: str, max_tokens: int | None = None) -> dict:
    """Ask the model for a single JSON object and parse it defensively."""
    import anyio

    _require_configured()
    effective_max_tokens = max_tokens or settings.ai_max_output_tokens

    def _call() -> str:
        if settings.ai_llm_provider == "gemini":
            # Gemini has a native JSON response mode -- no prompt instruction needed.
            return _gemini_complete(system, [LLMMessage(role="user", content=user_prompt)], effective_max_tokens, json_mode=True)
        return _anthropic_complete(
            system + "\n\nRespond with ONLY a single valid JSON object. No prose, no markdown fences.",
            [LLMMessage(role="user", content=user_prompt)],
            effective_max_tokens,
        )

    text = (await anyio.to_thread.run_sync(_call)).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        raise ValueError(f"LLM did not return valid JSON: {text[:200]!r}") from exc
