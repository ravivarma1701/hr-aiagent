"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-02-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    role_enum = sa.Enum("ADMIN", "MANAGER", "EMPLOYEE", name="role", native_enum=False)
    employee_status_enum = sa.Enum("ACTIVE", "INACTIVE", name="employeestatus", native_enum=False)
    attendance_status_enum = sa.Enum("ON_TIME", "LATE", "WFH", "ABSENT", name="attendancestatus", native_enum=False)

    op.create_table(
        "business_units",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("head_employee_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["head_employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_business_units_id"), "business_units", ["id"], unique=False)

    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("business_unit_id", sa.Integer(), nullable=False),
        sa.Column("location", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(["business_unit_id"], ["business_units.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_departments_business_unit_id"), "departments", ["business_unit_id"], unique=False)
    op.create_index(op.f("ix_departments_id"), "departments", ["id"], unique=False)
    op.create_index(op.f("ix_departments_location"), "departments", ["location"], unique=False)
    op.create_index(op.f("ix_departments_name"), "departments", ["name"], unique=False)

    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("manager_id", sa.Integer(), nullable=True),
        sa.Column("role", role_enum, nullable=False),
        sa.Column("status", employee_status_enum, nullable=False),
        sa.Column("joining_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["manager_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_employees_department_id"), "employees", ["department_id"], unique=False)
    op.create_index(op.f("ix_employees_email"), "employees", ["email"], unique=True)
    op.create_index(op.f("ix_employees_id"), "employees", ["id"], unique=False)
    op.create_index(op.f("ix_employees_name"), "employees", ["name"], unique=False)
    op.create_index(op.f("ix_employees_status"), "employees", ["status"], unique=False)

    op.create_table(
        "attendance_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("clock_in", sa.Time(), nullable=True),
        sa.Column("clock_out", sa.Time(), nullable=True),
        sa.Column("status", attendance_status_enum, nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_attendance_logs_date"), "attendance_logs", ["date"], unique=False)
    op.create_index(op.f("ix_attendance_logs_employee_id"), "attendance_logs", ["employee_id"], unique=False)
    op.create_index(op.f("ix_attendance_logs_id"), "attendance_logs", ["id"], unique=False)
    op.create_index(op.f("ix_attendance_logs_status"), "attendance_logs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_attendance_logs_status"), table_name="attendance_logs")
    op.drop_index(op.f("ix_attendance_logs_id"), table_name="attendance_logs")
    op.drop_index(op.f("ix_attendance_logs_employee_id"), table_name="attendance_logs")
    op.drop_index(op.f("ix_attendance_logs_date"), table_name="attendance_logs")
    op.drop_table("attendance_logs")

    op.drop_index(op.f("ix_employees_status"), table_name="employees")
    op.drop_index(op.f("ix_employees_name"), table_name="employees")
    op.drop_index(op.f("ix_employees_id"), table_name="employees")
    op.drop_index(op.f("ix_employees_email"), table_name="employees")
    op.drop_index(op.f("ix_employees_department_id"), table_name="employees")
    op.drop_table("employees")

    op.drop_index(op.f("ix_departments_name"), table_name="departments")
    op.drop_index(op.f("ix_departments_location"), table_name="departments")
    op.drop_index(op.f("ix_departments_id"), table_name="departments")
    op.drop_index(op.f("ix_departments_business_unit_id"), table_name="departments")
    op.drop_table("departments")

    op.drop_index(op.f("ix_business_units_id"), table_name="business_units")
    op.drop_table("business_units")
