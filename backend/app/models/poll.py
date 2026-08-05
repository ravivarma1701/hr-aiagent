from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Poll(Base):
    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    question: Mapped[str] = mapped_column(String(300))
    options: Mapped[list[str]] = mapped_column(JSON)
    created_by: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
