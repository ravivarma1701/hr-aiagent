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
from app.services.ai import intent_router
from app.services.ai.audit import log_ai_interaction
from app.services.ai.graph import run_chat_graph
from app.services.ai.llm_client import LLMMessage
from app.services.auth import get_current_user, oauth2_scheme

logger = structlog.get_logger()

router = APIRouter()


def _to_llm_messages(history: list) -> list[LLMMessage]:
    return [LLMMessage(role=item.role, content=item.content) for item in history]


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
    restriction in the permissions matrix. Runs through the LangGraph
    pipeline (graph.py) with intent forced to POLICY_QA; the graph's own
    audit_log node records the interaction."""
    try:
        result = await run_chat_graph(db=db, user=current_user, message=payload.message, forced_intent="POLICY_QA")
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

    return success_response({"answer": result["answer"], "sources": result["sources"]})


@router.post("/sql")
async def chat_sql(
    payload: ChatSQLRequest,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SQL Agent: read-only, role-scoped natural-language data lookups. Runs
    through the LangGraph pipeline with intent forced to SQL_QUERY."""
    try:
        result = await run_chat_graph(db=db, user=current_user, message=payload.message, forced_intent="SQL_QUERY")
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
    branches."""
    pending_action = payload.pending_action.model_dump() if payload.pending_action else None
    try:
        result = await run_chat_graph(
            db=db,
            user=current_user,
            access_token=access_token,
            message=payload.message,
            history=_to_llm_messages(payload.history),
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
    (graph.py) and don't call this."""
    try:
        result = await intent_router.classify_intent(payload.message, _to_llm_messages(payload.history))
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
