"""AI audit logging.

Every AI interaction is recorded: who asked, their role, what they asked,
what was detected/executed, and the outcome. Message text, tool name, and
record ids are stored; access tokens, passwords, and raw payroll/bank
values are never written here.
"""

from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_audit_log import AIAuditLog
from app.models.employee import Employee

MAX_MESSAGE_LENGTH = 4000


async def log_ai_interaction(
    db: AsyncSession,
    user: Employee,
    message: str,
    intent: str | None,
    tool_name: str | None,
    action_status: str,
    records_accessed: list | dict | None = None,
    error_reason: str | None = None,
    latency_ms: int | None = None,
) -> None:
    entry = AIAuditLog(
        user_id=user.id,
        role=user.role.value,
        message=(message or "")[:MAX_MESSAGE_LENGTH],
        intent=intent,
        tool_name=tool_name,
        action_status=action_status,
        records_accessed=json.dumps(records_accessed, default=str) if records_accessed is not None else None,
        error_reason=(error_reason or "")[:255] or None,
        latency_ms=latency_ms,
    )
    db.add(entry)
    await db.commit()
