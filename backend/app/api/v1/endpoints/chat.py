import json

import structlog
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import error_response, success_response
from app.db.session import get_db
from app.models.chat_session import ChatSession
from app.models.employee import Employee
from app.schemas.chat import (
    ChatActionRequest,
    ChatPolicyRequest,
    ChatRouterRequest,
    ChatSessionCreate,
    ChatSQLRequest,
    ChatStreamRequest,
)
from app.services.ai import chat_sessions, intent_router
from app.services.ai.audit import log_ai_interaction
from app.services.ai.graph import run_chat_graph, stream_chat_graph
from app.services.ai.llm_client import LLMMessage
from app.services.auth import get_current_user, oauth2_scheme

logger = structlog.get_logger()

router = APIRouter()

SESSION_NOT_FOUND = error_response("SESSION_NOT_FOUND", "Chat session not found.")


async def _resolve_session(db: AsyncSession, current_user: Employee, session_id: int | None) -> ChatSession | None:
    """Returns the owned session for session_id, or None if session_id was
    not given. Raises nothing -- an owned-lookup miss is reported by the
    caller as a 404 via SESSION_NOT_FOUND, never distinguishing "doesn't
    exist" from "belongs to someone else."""
    if session_id is None:
        return None
    return await chat_sessions.get_owned_session(db, current_user, session_id)


@router.post("/sessions")
async def create_or_get_chat_session(
    payload: ChatSessionCreate,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get-or-create the current user's one continuous AI Copilot session.
    Idempotent: calling this again for the same user returns the same
    session rather than creating a second one (also enforced at the DB
    level by a unique constraint on chat_sessions.user_id)."""
    _ = payload  # title is currently fixed; kept in the schema for forward compatibility
    session = await chat_sessions.get_or_create_session(db, current_user)
    return success_response({"id": session.id, "title": session.title, "created_at": session.created_at})


@router.get("/sessions/{session_id}/messages")
async def list_chat_session_messages(
    session_id: int,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full transcript for resuming a session on page load. Only
    role/content/route are stored -- rich artifacts (sources, SQL rows,
    action results) are not persisted, so resumed messages render as plain
    text."""
    session = await chat_sessions.get_owned_session(db, current_user, session_id)
    if session is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=SESSION_NOT_FOUND)

    messages = await chat_sessions.list_messages(db, session)
    return success_response(
        [
            {"id": m.id, "role": m.role, "content": m.content, "route": m.route, "created_at": m.created_at}
            for m in messages
        ]
    )


@router.post("/policy")
async def chat_policy(
    payload: ChatPolicyRequest,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Policy RAG Assistant: answers HR policy questions grounded in the
    policy library. Available to every role -- policy Q&A has no access
    restriction in the permissions matrix. Runs through the LangGraph
    pipeline (graph.py) with intent forced to POLICY_QA; the graph's own
    audit_log node records the interaction. If session_id is given, prior
    turns from that session are used as context and this exchange is
    appended to it afterward."""
    session = await _resolve_session(db, current_user, payload.session_id)
    if payload.session_id is not None and session is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=SESSION_NOT_FOUND)

    history: list[LLMMessage] = await chat_sessions.recent_history_for_llm(db, session) if session else []

    try:
        result = await run_chat_graph(
            db=db, user=current_user, message=payload.message, history=history, forced_intent="POLICY_QA"
        )
    except Exception:
        logger.exception("policy_chat_failed", user_id=current_user.id)
        await log_ai_interaction(
            db, current_user, payload.message, intent="POLICY_QA", tool_name=None,
            action_status="error", error_reason="unhandled_exception",
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response("POLICY_CHAT_FAILED", "Something went wrong answering that question."),
        )

    if session is not None:
        await chat_sessions.append_message(db, session, "user", payload.message, route="POLICY_QA")
        await chat_sessions.append_message(db, session, "assistant", result["answer"], route="POLICY_QA")

    return success_response({"answer": result["answer"], "sources": result["sources"]})


@router.post("/sql")
async def chat_sql(
    payload: ChatSQLRequest,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SQL Agent: read-only, role-scoped natural-language data lookups. Runs
    through the LangGraph pipeline with intent forced to SQL_QUERY. Session
    handling mirrors /policy."""
    session = await _resolve_session(db, current_user, payload.session_id)
    if payload.session_id is not None and session is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=SESSION_NOT_FOUND)

    history: list[LLMMessage] = await chat_sessions.recent_history_for_llm(db, session) if session else []

    try:
        result = await run_chat_graph(
            db=db, user=current_user, message=payload.message, history=history, forced_intent="SQL_QUERY"
        )
    except Exception:
        logger.exception("sql_chat_failed", user_id=current_user.id)
        await log_ai_interaction(
            db, current_user, payload.message, intent="SQL_QUERY", tool_name=None,
            action_status="error", error_reason="unhandled_exception",
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response("SQL_CHAT_FAILED", "Something went wrong answering that question."),
        )

    if session is not None:
        await chat_sessions.append_message(db, session, "user", payload.message, route="SQL_QUERY")
        await chat_sessions.append_message(db, session, "assistant", result["answer"], route="SQL_QUERY")

    return success_response({"answer": result["answer"], "sql": result["sql"], "rows": result["rows"]})


@router.post("/actions")
async def chat_actions(
    payload: ChatActionRequest,
    current_user: Employee = Depends(get_current_user),
    access_token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """HR Task Automation Agent: interprets the message into a backend API
    tool call made with the current user's own credentials. Never mutates
    the database directly. Runs through the LangGraph pipeline with intent
    forced to HR_ACTION; confirmation round-trips (confirm/pending_action)
    are handled by the graph's action_permission_check/action_confirm
    branches. Session handling mirrors /policy."""
    session = await _resolve_session(db, current_user, payload.session_id)
    if payload.session_id is not None and session is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=SESSION_NOT_FOUND)

    history: list[LLMMessage] = await chat_sessions.recent_history_for_llm(db, session) if session else []
    pending_action = payload.pending_action.model_dump() if payload.pending_action else None
    try:
        result = await run_chat_graph(
            db=db,
            user=current_user,
            access_token=access_token,
            message=payload.message,
            history=history,
            forced_intent="HR_ACTION",
            confirm=payload.confirm,
            pending_action=pending_action,
        )
    except Exception:
        logger.exception("action_chat_failed", user_id=current_user.id)
        await log_ai_interaction(
            db, current_user, payload.message, intent="HR_ACTION", tool_name=None,
            action_status="error", error_reason="unhandled_exception",
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response("ACTION_CHAT_FAILED", "Something went wrong performing that action."),
        )

    if session is not None:
        await chat_sessions.append_message(db, session, "user", payload.message, route="HR_ACTION")
        await chat_sessions.append_message(db, session, "assistant", result["answer"], route="HR_ACTION")

    return success_response(result)


@router.post("/router")
async def chat_router(
    payload: ChatRouterRequest,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Optional lightweight classifier: reports which agent a message would
    route to, without running the full pipeline. The /policy, /sql, and
    /actions endpoints do their own routing via the LangGraph pipeline
    (graph.py) and don't call this. If session_id is given, prior turns are
    used as classification context, but this call never writes to the
    session -- it's a preview, not a real turn, and the endpoint that
    actually handles the message persists it instead (avoids double-
    recording the same user message)."""
    session = await _resolve_session(db, current_user, payload.session_id)
    if payload.session_id is not None and session is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=SESSION_NOT_FOUND)

    history: list[LLMMessage] = await chat_sessions.recent_history_for_llm(db, session) if session else []

    try:
        result = await intent_router.classify_intent(payload.message, history)
    except Exception:
        logger.exception("router_chat_failed", user_id=current_user.id)
        await log_ai_interaction(
            db, current_user, payload.message, intent=None, tool_name="router",
            action_status="error", error_reason="unhandled_exception",
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response("ROUTER_CHAT_FAILED", "Something went wrong classifying that message."),
        )

    await log_ai_interaction(
        db, current_user, payload.message, intent=result["intent"], tool_name="router",
        action_status="classified",
    )
    return success_response(result)


@router.post("/stream")
async def chat_stream(
    payload: ChatStreamRequest,
    current_user: Employee = Depends(get_current_user),
    access_token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Streaming variant of /policy, /sql, /actions: same LangGraph
    pipeline (graph.py), but emits stage-progress events as each node
    completes -- "Understanding your request...", "Checking
    permissions...", "Calling the backend API..." -- instead of blocking
    until the whole response is ready. Not a replacement: /policy, /sql,
    /actions are unchanged and still used for testing/eval. forced_intent
    is required here since Auto-mode classification still happens via a
    separate /chat/router call before this endpoint is invoked."""
    session = await _resolve_session(db, current_user, payload.session_id)
    if payload.session_id is not None and session is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=SESSION_NOT_FOUND)

    history: list[LLMMessage] = await chat_sessions.recent_history_for_llm(db, session) if session else []
    pending_action = payload.pending_action.model_dump() if payload.pending_action else None

    async def event_generator():
        try:
            final_data = None
            async for event in stream_chat_graph(
                db=db,
                user=current_user,
                access_token=access_token,
                message=payload.message,
                history=history,
                forced_intent=payload.forced_intent,
                confirm=payload.confirm,
                pending_action=pending_action,
            ):
                if event["type"] == "final":
                    final_data = event["data"]
                yield f"data: {json.dumps(event, default=str)}\n\n"
        except Exception:
            logger.exception("stream_chat_failed", user_id=current_user.id)
            await log_ai_interaction(
                db, current_user, payload.message, intent=payload.forced_intent, tool_name=None,
                action_status="error", error_reason="unhandled_exception",
            )
            yield f"data: {json.dumps({'type': 'error', 'message': 'Something went wrong.'})}\n\n"
            return

        if session is not None and final_data is not None:
            await chat_sessions.append_message(db, session, "user", payload.message, route=payload.forced_intent)
            await chat_sessions.append_message(db, session, "assistant", final_data.get("answer", ""), route=payload.forced_intent)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
