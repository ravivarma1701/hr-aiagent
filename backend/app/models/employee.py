from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import EmployeeStatus, Role


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True, index=True)
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.EMPLOYEE)
    status: Mapped[EmployeeStatus] = mapped_column(Enum(EmployeeStatus), default=EmployeeStatus.ACTIVE, index=True)
    joining_date: Mapped[date] = mapped_column(Date)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    blood_type: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    occupancy: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    profile_photo_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_photo_mime: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_salary_usd: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bank_account_number: Mapped[str | None] = mapped_column(String(34), nullable=True)
    bank_account_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bank_branch: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bank_ifsc: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pan_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pan_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    pan_dob: Mapped[date | None] = mapped_column(Date, nullable=True)

    department = relationship("Department", back_populates="employees")
