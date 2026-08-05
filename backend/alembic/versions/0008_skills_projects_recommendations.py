"""skills and projects for recommendations

Revision ID: 0008_skills_projects_reco
Revises: 0007_attendance_mode_punctuality
Create Date: 2026-02-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008_skills_projects_reco"
down_revision: Union[str, None] = "0007_attendance_mode_punctuality"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    skill_level_enum = sa.Enum("BEGINNER", "INTERMEDIATE", "EXPERT", name="skilllevel", native_enum=False)

    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("normalized_name"),
    )
    op.create_index(op.f("ix_skills_id"), "skills", ["id"], unique=False)
    op.create_index(op.f("ix_skills_normalized_name"), "skills", ["normalized_name"], unique=False)

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_id"), "projects", ["id"], unique=False)
    op.create_index(op.f("ix_projects_name"), "projects", ["name"], unique=False)

    op.create_table(
        "employee_skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("level", skill_level_enum, nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "skill_id", name="uq_employee_skill"),
    )
    op.create_index(op.f("ix_employee_skills_id"), "employee_skills", ["id"], unique=False)
    op.create_index(op.f("ix_employee_skills_employee_id"), "employee_skills", ["employee_id"], unique=False)
    op.create_index(op.f("ix_employee_skills_skill_id"), "employee_skills", ["skill_id"], unique=False)

    op.create_table(
        "employee_projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("role_on_project", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "project_id", name="uq_employee_project"),
    )
    op.create_index(op.f("ix_employee_projects_id"), "employee_projects", ["id"], unique=False)
    op.create_index(op.f("ix_employee_projects_employee_id"), "employee_projects", ["employee_id"], unique=False)
    op.create_index(op.f("ix_employee_projects_project_id"), "employee_projects", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_employee_projects_project_id"), table_name="employee_projects")
    op.drop_index(op.f("ix_employee_projects_employee_id"), table_name="employee_projects")
    op.drop_index(op.f("ix_employee_projects_id"), table_name="employee_projects")
    op.drop_table("employee_projects")

    op.drop_index(op.f("ix_employee_skills_skill_id"), table_name="employee_skills")
    op.drop_index(op.f("ix_employee_skills_employee_id"), table_name="employee_skills")
    op.drop_index(op.f("ix_employee_skills_id"), table_name="employee_skills")
    op.drop_table("employee_skills")

    op.drop_index(op.f("ix_projects_name"), table_name="projects")
    op.drop_index(op.f("ix_projects_id"), table_name="projects")
    op.drop_table("projects")

    op.drop_index(op.f("ix_skills_normalized_name"), table_name="skills")
    op.drop_index(op.f("ix_skills_id"), table_name="skills")
    op.drop_table("skills")

