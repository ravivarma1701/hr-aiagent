from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PollResponse(Base):
    __tablename__ = "poll_responses"
    __table_args__ = (UniqueConstraint("poll_id", "employee_id", name="uq_poll_employee_response"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey("polls.id"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    option_index: Mapped[int] = mapped_column(index=True)
