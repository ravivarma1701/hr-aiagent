from datetime import date

from sqlalchemy import Date, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PayrollRecord(Base):
    __tablename__ = "payroll_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    month: Mapped[date] = mapped_column(Date, index=True)
    gross: Mapped[float] = mapped_column(Float)
    deductions: Mapped[dict] = mapped_column(JSON)
    net: Mapped[float] = mapped_column(Float)
    pan: Mapped[str] = mapped_column(String(20), index=True)
    pf_uan: Mapped[str | None] = mapped_column(String(30), nullable=True)
    esi_no: Mapped[str | None] = mapped_column(String(30), nullable=True)
