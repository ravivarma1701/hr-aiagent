"""Persisted AI Copilot conversation memory.

One continuous session per user (not a multi-session picker) -- see
models/chat_session.py. This module is the only place that reads/writes
`chat_sessions`/`chat_messages`, so ownership enforcement (a session must
belong to the requesting user) lives in exactly one function
(`get_owned_session`) rather than being re-implemented per endpoint.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.employee import Employee
from app.services.ai.llm_client import LLMMessage

DEFAULT_HISTORY_LIMIT = 10


async def get_or_create_session(db: AsyncSession, user: Employee) -> ChatSession:
    existing = (
        await db.execute(select(ChatSession).where(ChatSession.user_id == user.id))
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    session = ChatSession(user_id=user.id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_owned_session(db: AsyncSession, user: Employee, session_id: int) -> ChatSession | None:
    """Returns None (never raises) if the session doesn't exist or belongs
    to someone else -- callers should turn that into a generic 404 without
    distinguishing the two cases, so a guessed id never confirms whether it
    belongs to another user."""
    return (
        await db.execute(
            select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user.id)
        )
    ).scalar_one_or_none()


async def append_message(
    db: AsyncSession, session: ChatSession, role: str, content: str, route: str | None = None
) -> ChatMessage:
    message = ChatMessage(session_id=session.id, role=role, content=content, route=route)
    db.add(message)
    session.updated_at = func.now()
    await db.commit()
    await db.refresh(message)
    return message


async def list_messages(db: AsyncSession, session: ChatSession) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.id.asc())
    )
    return list(result.scalars().all())


async def recent_history_for_llm(
    db: AsyncSession, session: ChatSession, limit: int = DEFAULT_HISTORY_LIMIT
) -> list[LLMMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.id.desc())
        .limit(limit)
    )
    recent = list(result.scalars().all())
    recent.reverse()  # chronological order for the LLM
    return [LLMMessage(role=m.role, content=m.content) for m in recent]
