from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import TicketCategory, TicketPriority, TicketStatus


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[TicketCategory] = mapped_column(Enum(TicketCategory), index=True)
    priority: Mapped[TicketPriority] = mapped_column(Enum(TicketPriority), index=True)
    status: Mapped[TicketStatus] = mapped_column(Enum(TicketStatus), index=True, default=TicketStatus.OPEN)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
