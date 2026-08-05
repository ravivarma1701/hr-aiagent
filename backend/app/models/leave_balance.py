from sqlalchemy import Enum, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import LeaveType


class LeaveBalance(Base):
    __tablename__ = "leave_balances"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    leave_type: Mapped[LeaveType] = mapped_column(Enum(LeaveType), index=True)
    total: Mapped[float] = mapped_column(Float, default=12.0)
    used: Mapped[float] = mapped_column(Float, default=0.0)
    remaining: Mapped[float] = mapped_column(Float, default=12.0)
