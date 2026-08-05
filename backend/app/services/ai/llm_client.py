"""Thin, provider-agnostic wrapper around the LLM used for generation.

Only Anthropic's Claude API is implemented today, but callers depend on the
small interface below (``complete`` / ``complete_json``) rather than the
Anthropic SDK directly, so a second provider could be added without touching
the agents. The client is constructed lazily so importing this module never
fails when ANTHROPIC_API_KEY is not configured yet -- callers get a clear
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


_client = None


def _get_anthropic_client():
    global _client
    if _client is not None:
        return _client

    if not settings.anthropic_api_key:
        raise AIUnavailableError(
            "ANTHROPIC_API_KEY is not configured. Set it in backend/.env to enable AI generation."
        )

    import anthropic

    _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def is_configured() -> bool:
    return bool(settings.anthropic_api_key)


async def complete(system: str, messages: list[LLMMessage], max_tokens: int | None = None) -> str:
    """Single-turn (or multi-turn) text completion. Raises AIUnavailableError if unconfigured."""
    import anyio

    def _call() -> str:
        client = _get_anthropic_client()
        response = client.messages.create(
            model=settings.ai_model_name,
            max_tokens=max_tokens or settings.ai_max_output_tokens,
            system=system,
            messages=[{"role": m.role, "content": m.content} for m in messages],
        )
        return "".join(block.text for block in response.content if block.type == "text")

    return await anyio.to_thread.run_sync(_call)


async def complete_with_tools(system: str, user_prompt: str, tools: list[dict], max_tokens: int | None = None) -> dict:
    """Single-turn call that may result in a tool call. Returns
    {"text": str, "tool_calls": [{"name": str, "input": dict}]}."""
    import anyio

    def _call() -> dict:
        client = _get_anthropic_client()
        response = client.messages.create(
            model=settings.ai_model_name,
            max_tokens=max_tokens or settings.ai_max_output_tokens,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
            tools=tools,
        )
        text_parts = [block.text for block in response.content if block.type == "text"]
        tool_calls = [
            {"name": block.name, "input": block.input} for block in response.content if block.type == "tool_use"
        ]
        return {"text": "\n".join(text_parts).strip(), "tool_calls": tool_calls}

    return await anyio.to_thread.run_sync(_call)


async def complete_json(system: str, user_prompt: str, max_tokens: int | None = None) -> dict:
    """Ask the model for a single JSON object and parse it defensively."""
    text = await complete(
        system=system + "\n\nRespond with ONLY a single valid JSON object. No prose, no markdown fences.",
        messages=[LLMMessage(role="user", content=user_prompt)],
        max_tokens=max_tokens,
    )
    text = text.strip()
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
