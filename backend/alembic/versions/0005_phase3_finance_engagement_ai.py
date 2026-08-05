"""phase3 finance engagement ai schema

Revision ID: 0005_phase3_ai
Revises: 0004_ticket_management
Create Date: 2026-02-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_phase3_ai"
down_revision: Union[str, None] = "0004_ticket_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("phone", sa.String(length=20), nullable=True))
    op.add_column("employees", sa.Column("address", sa.String(length=255), nullable=True))
    op.add_column("employees", sa.Column("blood_type", sa.String(length=8), nullable=True))
    op.add_column("employees", sa.Column("occupancy", sa.String(length=60), nullable=True))
    op.create_index(op.f("ix_employees_blood_type"), "employees", ["blood_type"], unique=False)
    op.create_index(op.f("ix_employees_occupancy"), "employees", ["occupancy"], unique=False)

    op.create_table(
        "payroll_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("gross", sa.Float(), nullable=False),
        sa.Column("deductions", sa.JSON(), nullable=False),
        sa.Column("net", sa.Float(), nullable=False),
        sa.Column("pan", sa.String(length=20), nullable=False),
        sa.Column("pf_uan", sa.String(length=30), nullable=True),
        sa.Column("esi_no", sa.String(length=30), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payroll_records_id"), "payroll_records", ["id"], unique=False)
    op.create_index(op.f("ix_payroll_records_employee_id"), "payroll_records", ["employee_id"], unique=False)
    op.create_index(op.f("ix_payroll_records_month"), "payroll_records", ["month"], unique=False)
    op.create_index(op.f("ix_payroll_records_pan"), "payroll_records", ["pan"], unique=False)

    op.create_table(
        "polls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(length=300), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_polls_id"), "polls", ["id"], unique=False)
    op.create_index(op.f("ix_polls_created_by"), "polls", ["created_by"], unique=False)
    op.create_index(op.f("ix_polls_created_at"), "polls", ["created_at"], unique=False)

    op.create_table(
        "poll_responses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("poll_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("option_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["poll_id"], ["polls.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("poll_id", "employee_id", name="uq_poll_employee_response"),
    )
    op.create_index(op.f("ix_poll_responses_id"), "poll_responses", ["id"], unique=False)
    op.create_index(op.f("ix_poll_responses_poll_id"), "poll_responses", ["poll_id"], unique=False)
    op.create_index(op.f("ix_poll_responses_employee_id"), "poll_responses", ["employee_id"], unique=False)
    op.create_index(op.f("ix_poll_responses_option_index"), "poll_responses", ["option_index"], unique=False)

    op.create_table(
        "job_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("designation", sa.String(length=120), nullable=False),
        sa.Column("business_unit", sa.String(length=120), nullable=False),
        sa.Column("department", sa.String(length=120), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_job_history_id"), "job_history", ["id"], unique=False)
    op.create_index(op.f("ix_job_history_employee_id"), "job_history", ["employee_id"], unique=False)
    op.create_index(op.f("ix_job_history_start_date"), "job_history", ["start_date"], unique=False)
    op.create_index(op.f("ix_job_history_end_date"), "job_history", ["end_date"], unique=False)
    op.create_index(op.f("ix_job_history_is_current"), "job_history", ["is_current"], unique=False)

    op.create_table(
        "hr_policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_hr_policies_id"), "hr_policies", ["id"], unique=False)
    op.create_index(op.f("ix_hr_policies_title"), "hr_policies", ["title"], unique=False)
    op.create_index(op.f("ix_hr_policies_category"), "hr_policies", ["category"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_hr_policies_category"), table_name="hr_policies")
    op.drop_index(op.f("ix_hr_policies_title"), table_name="hr_policies")
    op.drop_index(op.f("ix_hr_policies_id"), table_name="hr_policies")
    op.drop_table("hr_policies")

    op.drop_index(op.f("ix_job_history_is_current"), table_name="job_history")
    op.drop_index(op.f("ix_job_history_end_date"), table_name="job_history")
    op.drop_index(op.f("ix_job_history_start_date"), table_name="job_history")
    op.drop_index(op.f("ix_job_history_employee_id"), table_name="job_history")
    op.drop_index(op.f("ix_job_history_id"), table_name="job_history")
    op.drop_table("job_history")

    op.drop_index(op.f("ix_poll_responses_option_index"), table_name="poll_responses")
    op.drop_index(op.f("ix_poll_responses_employee_id"), table_name="poll_responses")
    op.drop_index(op.f("ix_poll_responses_poll_id"), table_name="poll_responses")
    op.drop_index(op.f("ix_poll_responses_id"), table_name="poll_responses")
    op.drop_table("poll_responses")

    op.drop_index(op.f("ix_polls_created_at"), table_name="polls")
    op.drop_index(op.f("ix_polls_created_by"), table_name="polls")
    op.drop_index(op.f("ix_polls_id"), table_name="polls")
    op.drop_table("polls")

    op.drop_index(op.f("ix_payroll_records_pan"), table_name="payroll_records")
    op.drop_index(op.f("ix_payroll_records_month"), table_name="payroll_records")
    op.drop_index(op.f("ix_payroll_records_employee_id"), table_name="payroll_records")
    op.drop_index(op.f("ix_payroll_records_id"), table_name="payroll_records")
    op.drop_table("payroll_records")

    op.drop_index(op.f("ix_employees_occupancy"), table_name="employees")
    op.drop_index(op.f("ix_employees_blood_type"), table_name="employees")
    op.drop_column("employees", "occupancy")
    op.drop_column("employees", "blood_type")
    op.drop_column("employees", "address")
    op.drop_column("employees", "phone")
