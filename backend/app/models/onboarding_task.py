from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    task_name: Mapped[str] = mapped_column(String(200))
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
