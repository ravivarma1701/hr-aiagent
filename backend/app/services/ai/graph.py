"""LangGraph orchestration for the AI Copilot.

Implements the pipeline the assignment's "AI Router" / "LangGraph
Multi-Agent Orchestration" sections describe:

    START -> load_user_context -> classify_intent -> route
        -> policy_agent | sql_agent_node
        -> action_propose -> action_permission_check -> action_confirm_gate -> action_execute
        -> unknown
    -> generate_final_response -> audit_log -> END

Each existing agent module (policy_rag, sql_agent, action_agent) already
exposes small, single-purpose async functions; this module's nodes are thin
wrappers that call them and shuttle results through a shared state dict, so
none of that logic is duplicated here -- this file is purely the wiring.

Permission enforcement still lives in exactly one place (permissions.py):
the ``action_permission_check`` node calls the same ``can_use_tool`` that
``action_agent._execute_tool`` also calls internally, so there is one
source of truth, not two gates that could drift apart.

The graph is compiled once at import time with no checkpointer -- every
request is a single, stateless ``ainvoke`` call. Human-in-the-loop
confirmation is handled with plain state fields (``confirm``,
``pending_action_in``) round-tripped through the HTTP API, not LangGraph's
``interrupt()``/checkpointer machinery, since that machinery is built for
long-lived, resumable threads and would add a persistence layer this
stateless request/response flow doesn't need.
"""

from __future__ import annotations

import time
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.models.employee import Employee
from app.models.enums import Role
from app.services.ai import action_agent, policy_rag, sql_agent
from app.services.ai.audit import log_ai_interaction
from app.services.ai.intent_router import classify_intent as classify_intent_llm
from app.services.ai.llm_client import LLMMessage
from app.services.ai.permissions import GENERIC_REFUSAL, can_use_tool, requires_confirmation


class ChatState(TypedDict, total=False):
    # --- input ---
    db: Any  # AsyncSession
    user: Employee
    access_token: str
    message: str
    history: list[LLMMessage]
    forced_intent: str | None
    confirm: bool
    pending_action_in: dict | None
    started_at: float
    role_allowed_tools: list[str]

    # --- routing ---
    intent: str
    confidence: float
    reason: str

    # --- action branch working state ---
    proposed_tool: str | None
    proposed_args: dict
    proposed_text: str
    permission_allowed: bool
    permission_reason: str

    # --- output (shape matches the /policy, /sql, /actions response payloads) ---
    answer: str
    sources: list
    sql: str | None
    rows: list
    action: str | None
    status: str
    result: Any
    pending_action: dict | None

    # --- audit ---
    tool_name_for_audit: str | None
    action_status_for_audit: str
    records_accessed: Any


# --- Nodes -------------------------------------------------------------------


async def node_load_user_context(state: ChatState) -> dict:
    """Records what this user's role is allowed to do, as its own pipeline
    step (matching the assignment's diagram) rather than folding it into
    classify_intent. `action_propose`/`action_permission_check` recompute
    their own role-scoped checks independently (via `_tools_for_role` /
    `can_use_tool`) rather than trusting this value, since those are the
    actual enforcement points and shouldn't depend on an earlier node
    having run correctly -- this node's output is for audit/tracing
    visibility, not authorization."""
    role: Role = state["user"].role
    return {"role_allowed_tools": [name for name in action_agent.TOOL_PERMISSIONS if role in action_agent.TOOL_PERMISSIONS[name]]}


async def node_classify_intent(state: ChatState) -> dict:
    if state.get("confirm") and state.get("pending_action_in"):
        # Fast path: resuming a previously-proposed action. Skip
        # classification and re-extraction entirely -- execute exactly
        # what was shown to the user, not a fresh LLM interpretation.
        return {"intent": "HR_ACTION", "confidence": 1.0, "reason": "resuming a confirmed pending action"}

    if state.get("forced_intent"):
        return {"intent": state["forced_intent"], "confidence": 1.0, "reason": "endpoint-specified"}

    classification = await classify_intent_llm(state["message"], state.get("history"))
    return classification


def route_after_classify(state: ChatState) -> str:
    if state.get("confirm") and state.get("pending_action_in"):
        return "action_permission_check"
    intent = state.get("intent")
    if intent == "POLICY_QA":
        return "policy_agent"
    if intent == "SQL_QUERY":
        return "sql_agent_node"
    if intent == "HR_ACTION":
        return "action_propose"
    return "unknown"


async def node_policy_agent(state: ChatState) -> dict:
    result = await policy_rag.answer_policy_question(state["message"])
    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "tool_name_for_audit": "policy_rag",
        "action_status_for_audit": "grounded" if result["grounded"] else "insufficient_context",
        "records_accessed": [s["title"] for s in result["sources"]],
    }


async def node_sql_agent(state: ChatState) -> dict:
    result = await sql_agent.answer_sql_question(state["message"], state["user"])
    row_ids = [row.get("id") for row in result["rows"] if isinstance(row, dict) and "id" in row][:50]
    action_status = "completed" if result["rows"] else ("blocked" if result["sql"] is None else "no_results")
    return {
        "answer": result["answer"],
        "sql": result["sql"],
        "rows": result["rows"],
        "tool_name_for_audit": "sql_agent",
        "action_status_for_audit": action_status,
        "records_accessed": row_ids,
    }


async def node_action_propose(state: ChatState) -> dict:
    proposal = await action_agent.propose_action(state["message"], state["user"].role, state.get("history"))
    return {
        "proposed_tool": proposal["tool_name"],
        "proposed_args": proposal["args"],
        "proposed_text": proposal["text"],
    }


def route_after_propose(state: ChatState) -> str:
    return "action_permission_check" if state.get("proposed_tool") else "no_tool"


async def node_action_permission_check(state: ChatState) -> dict:
    if state.get("confirm") and state.get("pending_action_in"):
        pending = state["pending_action_in"]
        tool_name = pending.get("tool_name")
        args = pending.get("arguments") or {}
    else:
        tool_name = state.get("proposed_tool")
        args = state.get("proposed_args") or {}

    permission = can_use_tool(state["user"].role, tool_name)
    return {
        "proposed_tool": tool_name,
        "proposed_args": args,
        "permission_allowed": permission.allowed,
        "permission_reason": permission.reason or GENERIC_REFUSAL,
    }


def route_after_permission(state: ChatState) -> str:
    if not state.get("permission_allowed"):
        return "forbidden"
    if state.get("confirm") and state.get("pending_action_in"):
        # Already confirmed by the client -- go straight to execution.
        return "execute"
    if requires_confirmation(state.get("proposed_tool")):
        return "needs_confirmation"
    return "execute"


async def node_action_execute(state: ChatState) -> dict:
    result = await action_agent._execute_tool(
        state["proposed_tool"], state["proposed_args"], state["user"].role, state["access_token"]
    )
    return {
        "answer": result["answer"],
        "action": result["action"],
        "status": result["status"],
        "result": result["result"],
        "pending_action": result["pending_action"],
        "tool_name_for_audit": result["action"],
        "action_status_for_audit": result["status"],
        "records_accessed": [result["result"]["id"]] if isinstance(result["result"], dict) and "id" in result["result"] else None,
    }


async def node_action_forbidden(state: ChatState) -> dict:
    return {
        "answer": state["permission_reason"],
        "action": state.get("proposed_tool"),
        "status": "forbidden",
        "result": None,
        "pending_action": None,
        "tool_name_for_audit": state.get("proposed_tool"),
        "action_status_for_audit": "forbidden",
    }


async def node_action_needs_confirmation(state: ChatState) -> dict:
    tool_name = state["proposed_tool"]
    args = state["proposed_args"]
    return {
        "answer": action_agent._describe_proposed_action(tool_name, args),
        "action": tool_name,
        "status": "pending_confirmation",
        "result": None,
        "pending_action": {"tool_name": tool_name, "arguments": args},
        "tool_name_for_audit": tool_name,
        "action_status_for_audit": "pending_confirmation",
    }


async def node_action_no_tool(state: ChatState) -> dict:
    return {
        "answer": state.get("proposed_text") or "I'm not sure how to help with that.",
        "action": None,
        "status": "unavailable" if not action_agent.is_configured() else "no_action",
        "result": None,
        "pending_action": None,
        "tool_name_for_audit": None,
        "action_status_for_audit": "unavailable" if not action_agent.is_configured() else "no_action",
    }


async def node_unknown(state: ChatState) -> dict:
    return {
        "answer": "I'm not sure whether that's a policy question, a data lookup, or a task. Could you rephrase?",
        "tool_name_for_audit": None,
        "action_status_for_audit": "unknown_intent",
    }


async def node_generate_final_response(state: ChatState) -> dict:
    """Normalizes whichever branch ran into the common response shape. Kept
    as its own node (rather than folded into each branch) to match the
    assignment's pipeline diagram and to be the single place that could add
    cross-cutting formatting later (e.g. trimming, redaction) without
    touching every agent branch."""
    return {
        "answer": state.get("answer", ""),
        "sources": state.get("sources", []),
        "sql": state.get("sql"),
        "rows": state.get("rows", []),
        "action": state.get("action"),
        "status": state.get("status", "n/a"),
        "result": state.get("result"),
        "pending_action": state.get("pending_action"),
    }


async def node_audit_log(state: ChatState) -> dict:
    started_at = state.get("started_at")
    latency_ms = int((time.monotonic() - started_at) * 1000) if started_at is not None else None
    await log_ai_interaction(
        state["db"],
        state["user"],
        state["message"],
        intent=state.get("intent"),
        tool_name=state.get("tool_name_for_audit"),
        action_status=state.get("action_status_for_audit", "unknown"),
        records_accessed=state.get("records_accessed"),
        latency_ms=latency_ms,
    )
    return {}


# --- Graph assembly ------------------------------------------------------


def _build_graph():
    graph = StateGraph(ChatState)

    graph.add_node("load_user_context", node_load_user_context)
    graph.add_node("classify_intent", node_classify_intent)
    graph.add_node("policy_agent", node_policy_agent)
    graph.add_node("sql_agent_node", node_sql_agent)
    graph.add_node("action_propose", node_action_propose)
    graph.add_node("action_permission_check", node_action_permission_check)
    graph.add_node("action_execute", node_action_execute)
    graph.add_node("action_forbidden", node_action_forbidden)
    graph.add_node("action_needs_confirmation", node_action_needs_confirmation)
    graph.add_node("action_no_tool", node_action_no_tool)
    graph.add_node("unknown", node_unknown)
    graph.add_node("generate_final_response", node_generate_final_response)
    graph.add_node("audit_log", node_audit_log)

    graph.set_entry_point("load_user_context")
    graph.add_edge("load_user_context", "classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        route_after_classify,
        {
            "policy_agent": "policy_agent",
            "sql_agent_node": "sql_agent_node",
            "action_propose": "action_propose",
            "action_permission_check": "action_permission_check",
            "unknown": "unknown",
        },
    )

    graph.add_conditional_edges(
        "action_propose",
        route_after_propose,
        {"action_permission_check": "action_permission_check", "no_tool": "action_no_tool"},
    )

    graph.add_conditional_edges(
        "action_permission_check",
        route_after_permission,
        {"forbidden": "action_forbidden", "needs_confirmation": "action_needs_confirmation", "execute": "action_execute"},
    )

    for node in ("policy_agent", "sql_agent_node", "action_execute", "action_forbidden", "action_needs_confirmation", "action_no_tool", "unknown"):
        graph.add_edge(node, "generate_final_response")

    graph.add_edge("generate_final_response", "audit_log")
    graph.add_edge("audit_log", END)

    return graph.compile()


_compiled_graph = _build_graph()


async def run_chat_graph(
    *,
    db,
    user: Employee,
    access_token: str = "",
    message: str,
    history: list[LLMMessage] | None = None,
    forced_intent: str | None = None,
    confirm: bool = False,
    pending_action: dict | None = None,
) -> dict:
    initial_state: ChatState = {
        "db": db,
        "user": user,
        "access_token": access_token,
        "message": message,
        "history": history or [],
        "forced_intent": forced_intent,
        "confirm": confirm,
        "pending_action_in": pending_action,
        "started_at": time.monotonic(),
    }
    final_state = await _compiled_graph.ainvoke(initial_state)
    return {
        "answer": final_state.get("answer", ""),
        "sources": final_state.get("sources", []),
        "sql": final_state.get("sql"),
        "rows": final_state.get("rows", []),
        "action": final_state.get("action"),
        "status": final_state.get("status", "n/a"),
        "result": final_state.get("result"),
        "pending_action": final_state.get("pending_action"),
    }
