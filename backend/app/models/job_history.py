from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobHistory(Base):
    __tablename__ = "job_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    designation: Mapped[str] = mapped_column(String(120))
    business_unit: Mapped[str] = mapped_column(String(120))
    department: Mapped[str] = mapped_column(String(120))
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
