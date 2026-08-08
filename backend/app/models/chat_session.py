from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChatSession(Base):
    """One continuous AI Copilot conversation per user (not a multi-session
    picker) -- user_id is unique, so this is effectively a 1:1 with
    employees. See services/ai/chat_sessions.py for get-or-create logic."""

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    title: Mapped[str] = mapped_column(String(120), default="AI Copilot Conversation")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
