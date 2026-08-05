import time

import structlog
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import error_response, success_response
from app.db.session import get_db
from app.models.employee import Employee
from app.schemas.chat import (
    ChatActionRequest,
    ChatMessageCreate,
    ChatPolicyRequest,
    ChatRouterRequest,
    ChatSessionCreate,
    ChatSQLRequest,
)
from app.services.ai import action_agent, intent_router, policy_rag, sql_agent
from app.services.ai.audit import log_ai_interaction
from app.services.auth import get_current_user, oauth2_scheme

logger = structlog.get_logger()

router = APIRouter()


@router.post("/sessions")
async def create_chat_session(
    payload: ChatSessionCreate,
    current_user: Employee = Depends(get_current_user),
):
    _ = payload
    _ = current_user
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=error_response("CHAT_NOT_IMPLEMENTED", "Chat session creation is a Phase-3 stub and not implemented yet"),
    )


@router.post("/sessions/{session_id}/messages")
async def post_chat_message(
    session_id: str,
    payload: ChatMessageCreate,
    current_user: Employee = Depends(get_current_user),
):
    _ = session_id
    _ = payload
    _ = current_user
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=error_response("CHAT_NOT_IMPLEMENTED", "Chat messaging is a Phase-3 stub and not implemented yet"),
    )


@router.post("/policy")
async def chat_policy(
    payload: ChatPolicyRequest,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Policy RAG Assistant: answers HR policy questions grounded in the
    policy library. Available to every role -- policy Q&A has no access
    restriction in the permissions matrix."""
    started = time.monotonic()
    try:
        result = await policy_rag.answer_policy_question(payload.message)
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

    latency_ms = int((time.monotonic() - started) * 1000)
    await log_ai_interaction(
        db, current_user, payload.message, intent="POLICY_QA", tool_name="policy_rag",
        action_status="grounded" if result["grounded"] else "insufficient_context",
        records_accessed=[s["title"] for s in result["sources"]],
        latency_ms=latency_ms,
    )
    return success_response({"answer": result["answer"], "sources": result["sources"]})


@router.post("/sql")
async def chat_sql(
    payload: ChatSQLRequest,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SQL Agent: read-only, role-scoped natural-language data lookups."""
    started = time.monotonic()
    try:
        result = await sql_agent.answer_sql_question(payload.message, current_user)
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

    latency_ms = int((time.monotonic() - started) * 1000)
    action_status = "completed" if result["rows"] else ("blocked" if result["sql"] is None else "no_results")
    row_ids = [row.get("id") for row in result["rows"] if isinstance(row, dict) and "id" in row][:50]
    await log_ai_interaction(
        db, current_user, payload.message, intent="SQL_QUERY", tool_name="sql_agent",
        action_status=action_status, records_accessed=row_ids, latency_ms=latency_ms,
    )
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
    the database directly."""
    started = time.monotonic()
    pending_action = payload.pending_action.model_dump() if payload.pending_action else None
    try:
        result = await action_agent.handle_action_request(
            message=payload.message,
            user=current_user,
            access_token=access_token,
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

    latency_ms = int((time.monotonic() - started) * 1000)
    result_payload = result.get("result")
    records_accessed = None
    if isinstance(result_payload, dict) and "id" in result_payload:
        records_accessed = [result_payload["id"]]
    await log_ai_interaction(
        db, current_user, payload.message, intent="HR_ACTION", tool_name=result.get("action"),
        action_status=result["status"], records_accessed=records_accessed, latency_ms=latency_ms,
    )
    return success_response(result)


@router.post("/router")
async def chat_router(
    payload: ChatRouterRequest,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Optional unified router: classifies intent so a frontend can dispatch
    to the right agent without asking the user to pick one."""
    result = await intent_router.classify_intent(payload.message)
    await log_ai_interaction(
        db, current_user, payload.message, intent=result["intent"], tool_name="router",
        action_status="classified",
    )
    return success_response(result)
