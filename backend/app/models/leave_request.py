from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import HalfDayPeriod, LeaveRequestStatus, LeaveType


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    leave_type: Mapped[LeaveType] = mapped_column(Enum(LeaveType), index=True)
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date] = mapped_column(Date, index=True)
    reason: Mapped[str] = mapped_column(String(500))
    is_half_day: Mapped[bool] = mapped_column(Boolean, default=False)
    half_day_period: Mapped[HalfDayPeriod | None] = mapped_column(Enum(HalfDayPeriod), nullable=True)
    status: Mapped[LeaveRequestStatus] = mapped_column(Enum(LeaveRequestStatus), default=LeaveRequestStatus.PENDING, index=True)
    approver_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True, index=True)
