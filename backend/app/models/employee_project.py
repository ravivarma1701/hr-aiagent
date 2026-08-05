from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmployeeProject(Base):
    __tablename__ = "employee_projects"
    __table_args__ = (UniqueConstraint("employee_id", "project_id", name="uq_employee_project"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    role_on_project: Mapped[str | None] = mapped_column(String(120), nullable=True)
