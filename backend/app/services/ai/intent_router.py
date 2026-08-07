"""Classifies a chat message into POLICY_QA / SQL_QUERY / HR_ACTION / UNKNOWN.

Uses the LLM when configured (more accurate for phrasing it hasn't seen
before), and always falls back to a keyword heuristic so /chat/router keeps
working even without an API key.
"""

from __future__ import annotations

import re

import structlog

from app.services.ai.llm_client import LLMMessage, complete_json, is_configured

logger = structlog.get_logger()

VALID_INTENTS = {"POLICY_QA", "SQL_QUERY", "HR_ACTION", "UNKNOWN"}

_ACTION_PATTERNS = [
    r"\bapply\b", r"\bsubmit\b", r"\braise a ticket\b", r"\bcreate a ticket\b", r"\bcreate ticket\b",
    r"\bopen a ticket\b", r"\bapprove\b", r"\breject\b", r"\bassign\b", r"\bupdate ticket\b",
    r"\bpost an announcement\b", r"\bcreate an announcement\b", r"\bbook (a )?leave\b",
    r"\bcheck my (leave|ticket)\b",
]
_POLICY_PATTERNS = [
    r"\bpolicy\b", r"\bpolicies\b", r"\bhow many (sick|casual|earned)\b", r"\bwhat happens if\b",
    r"\bam i allowed\b", r"\bcan i (take|work)\b", r"\bwork(ing)? from home\b", r"\bwfh\b",
    r"\bhalf.?day\b", r"\bdress code\b", r"\bcode of conduct\b", r"\bprobation\b",
]
_SQL_PATTERNS = [
    r"\bwho is\b", r"\bwhich employees\b", r"\bshow (my|all)\b", r"\blist (all )?(projects|employees)\b",
    r"\bongoing projects\b", r"\bassigned to\b", r"\bknow (python|java|react|sql|fastapi|langchain)\b",
    r"\breport to\b", r"\bskills?\b", r"\bmy (current )?project", r"\bmy leave (balance|requests)\b",
]


def _heuristic(message: str) -> tuple[str, float, str]:
    text = message.lower()
    for pattern in _ACTION_PATTERNS:
        if re.search(pattern, text):
            return "HR_ACTION", 0.6, "Message contains an action verb typical of a task request."
    # SQL patterns are checked before policy patterns: phrases like "who is
    # assigned to <Project Name>" can contain the word "policy" inside a
    # proper noun (e.g. "HR Policy Copilot" project) and would otherwise be
    # misrouted to Policy QA.
    for pattern in _SQL_PATTERNS:
        if re.search(pattern, text):
            return "SQL_QUERY", 0.6, "Message asks to look up people/project/data records."
    for pattern in _POLICY_PATTERNS:
        if re.search(pattern, text):
            return "POLICY_QA", 0.6, "Message asks about a policy/rule rather than data or an action."
    return "UNKNOWN", 0.2, "Could not confidently classify the message with keyword heuristics."


_ROUTER_SYSTEM_PROMPT = """Classify the user's LATEST HR chat message into
exactly one of: POLICY_QA (asking about an HR policy/rule), SQL_QUERY
(asking to look up employees/projects/departments/skills/leave/ticket data),
HR_ACTION (asking to perform a mutation like applying for leave, creating a
ticket, approving/rejecting something, assigning someone, or posting an
announcement), or UNKNOWN.

If prior conversation turns are given, use them for context -- a short
reply like "its a casual leave" or "yes, confirm it" only makes sense in
light of what was asked or proposed just before it, and is very likely a
continuation of whatever the previous turn was about (often HR_ACTION,
answering a clarifying question).

Respond as JSON: {"intent": "POLICY_QA|SQL_QUERY|HR_ACTION|UNKNOWN", "confidence": 0.0-1.0, "reason": "short reason"}
"""


def _build_router_prompt(message: str, history: list[LLMMessage] | None) -> str:
    if not history:
        return message
    transcript = "\n".join(f"{'User' if m.role == 'user' else 'Assistant'}: {m.content}" for m in history)
    return f"Conversation so far:\n{transcript}\n\nLatest user message: {message}"


async def classify_intent(message: str, history: list[LLMMessage] | None = None) -> dict:
    if is_configured():
        try:
            prompt = _build_router_prompt(message, history)
            result = await complete_json(system=_ROUTER_SYSTEM_PROMPT, user_prompt=prompt, max_tokens=200)
            intent = result.get("intent")
            if intent in VALID_INTENTS:
                confidence = float(result.get("confidence", 0.5))
                return {"intent": intent, "confidence": max(0.0, min(1.0, confidence)), "reason": result.get("reason", "")}
        except Exception:
            # This function's entire contract is "always return a usable
            # classification" -- any provider-side failure (rate limit,
            # transient API error, malformed JSON, etc.) falls back to the
            # keyword heuristic below rather than propagating, so a flaky
            # LLM call never turns into a crashed request.
            logger.warning("intent_classification_llm_failed", exc_info=True)

    intent, confidence, reason = _heuristic(message)
    return {"intent": intent, "confidence": confidence, "reason": reason}
