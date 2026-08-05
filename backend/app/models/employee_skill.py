from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import SkillLevel


class EmployeeSkill(Base):
    __tablename__ = "employee_skills"
    __table_args__ = (UniqueConstraint("employee_id", "skill_id", name="uq_employee_skill"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), index=True)
    level: Mapped[SkillLevel] = mapped_column(Enum(SkillLevel), nullable=False)
