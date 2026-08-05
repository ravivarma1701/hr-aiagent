from datetime import date, time

from sqlalchemy import Date, Enum, ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import AttendanceStatus


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    clock_in: Mapped[time | None] = mapped_column(Time, nullable=True)
    clock_out: Mapped[time | None] = mapped_column(Time, nullable=True)
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus), index=True)
    work_mode: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    punctuality: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
