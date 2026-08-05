"""leave workflow schema

Revision ID: 0002_leave_workflow
Revises: 0001_initial
Create Date: 2026-02-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_leave_workflow"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    leave_type_enum = sa.Enum("CASUAL", "SICK", "EARNED", name="leavetype", native_enum=False)
    leave_request_status_enum = sa.Enum("PENDING", "APPROVED", "REJECTED", name="leaverequeststatus", native_enum=False)

    op.create_table(
        "leave_balances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("leave_type", leave_type_enum, nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("used", sa.Integer(), nullable=False),
        sa.Column("remaining", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_leave_balances_id"), "leave_balances", ["id"], unique=False)
    op.create_index(op.f("ix_leave_balances_employee_id"), "leave_balances", ["employee_id"], unique=False)
    op.create_index(op.f("ix_leave_balances_leave_type"), "leave_balances", ["leave_type"], unique=False)

    op.create_table(
        "leave_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("leave_type", leave_type_enum, nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("status", leave_request_status_enum, nullable=False),
        sa.Column("approver_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["approver_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_leave_requests_id"), "leave_requests", ["id"], unique=False)
    op.create_index(op.f("ix_leave_requests_employee_id"), "leave_requests", ["employee_id"], unique=False)
    op.create_index(op.f("ix_leave_requests_leave_type"), "leave_requests", ["leave_type"], unique=False)
    op.create_index(op.f("ix_leave_requests_start_date"), "leave_requests", ["start_date"], unique=False)
    op.create_index(op.f("ix_leave_requests_end_date"), "leave_requests", ["end_date"], unique=False)
    op.create_index(op.f("ix_leave_requests_status"), "leave_requests", ["status"], unique=False)
    op.create_index(op.f("ix_leave_requests_approver_id"), "leave_requests", ["approver_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_leave_requests_approver_id"), table_name="leave_requests")
    op.drop_index(op.f("ix_leave_requests_status"), table_name="leave_requests")
    op.drop_index(op.f("ix_leave_requests_end_date"), table_name="leave_requests")
    op.drop_index(op.f("ix_leave_requests_start_date"), table_name="leave_requests")
    op.drop_index(op.f("ix_leave_requests_leave_type"), table_name="leave_requests")
    op.drop_index(op.f("ix_leave_requests_employee_id"), table_name="leave_requests")
    op.drop_index(op.f("ix_leave_requests_id"), table_name="leave_requests")
    op.drop_table("leave_requests")

    op.drop_index(op.f("ix_leave_balances_leave_type"), table_name="leave_balances")
    op.drop_index(op.f("ix_leave_balances_employee_id"), table_name="leave_balances")
    op.drop_index(op.f("ix_leave_balances_id"), table_name="leave_balances")
    op.drop_table("leave_balances")

