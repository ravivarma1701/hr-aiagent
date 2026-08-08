from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChatMessage(Base):
    """A single persisted turn in a ChatSession. Only role/content/route are
    stored -- rich UI-only artifacts (policy sources, SQL rows, action
    result/pending_action) are NOT persisted, only ever used live in the
    original response. That's a deliberate scope boundary: role+content is
    everything the LLM needs for conversation continuity, and a plain-text
    transcript is enough to make a resumed session readable."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    route: Mapped[str | None] = mapped_column(String(20), nullable=True)  # POLICY_QA/SQL_QUERY/HR_ACTION/UNKNOWN
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False, index=True
    )
