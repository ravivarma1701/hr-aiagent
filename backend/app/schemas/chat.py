from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatSessionCreate(BaseModel):
    title: str = Field(default="AI Copilot Conversation", min_length=1, max_length=120)


class ChatSessionOut(BaseModel):
    id: int
    title: str
    created_at: datetime


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    route: str | None = None
    created_at: datetime


# --- Phase 4: AI copilot chat endpoints ------------------------------------


class ChatPolicyRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: int | None = None


class PolicySource(BaseModel):
    title: str
    category: str
    filename: str


class ChatPolicyResponse(BaseModel):
    answer: str
    sources: list[PolicySource]


class ChatSQLRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: int | None = None


class ChatSQLResponse(BaseModel):
    answer: str
    sql: str | None = None
    rows: list[dict]


class PendingAction(BaseModel):
    tool_name: str
    arguments: dict


class ChatActionRequest(BaseModel):
    message: str = Field(default="", max_length=2000)
    confirm: bool = False
    pending_action: PendingAction | None = None
    session_id: int | None = None


class ChatActionResponse(BaseModel):
    answer: str
    action: str | None = None
    status: str
    result: dict | list | None = None
    pending_action: PendingAction | None = None


class ChatRouterRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: int | None = None


class ChatRouterResponse(BaseModel):
    intent: str
    confidence: float
    reason: str


class ChatStreamRequest(BaseModel):
    """Union of what /policy, /sql, /actions each need -- forced_intent
    picks which agent handles the message (Auto-mode classification still
    happens via a separate /chat/router call before this one, unchanged)."""

    message: str = Field(default="", max_length=2000)
    forced_intent: Literal["POLICY_QA", "SQL_QUERY", "HR_ACTION"]
    session_id: int | None = None
    confirm: bool = False
    pending_action: PendingAction | None = None
