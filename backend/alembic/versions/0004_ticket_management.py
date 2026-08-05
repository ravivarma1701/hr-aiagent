"""ticket management schema

Revision ID: 0004_ticket_management
Revises: 0003_announcements
Create Date: 2026-02-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_ticket_management"
down_revision: Union[str, None] = "0003_announcements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    ticket_category_enum = sa.Enum("IT", "HR", "ONBOARDING", name="ticketcategory", native_enum=False)
    ticket_priority_enum = sa.Enum("LOW", "MEDIUM", "HIGH", name="ticketpriority", native_enum=False)
    ticket_status_enum = sa.Enum("OPEN", "IN_PROGRESS", "RESOLVED", name="ticketstatus", native_enum=False)

    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("assignee_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", ticket_category_enum, nullable=False),
        sa.Column("priority", ticket_priority_enum, nullable=False),
        sa.Column("status", ticket_status_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["assignee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tickets_id"), "tickets", ["id"], unique=False)
    op.create_index(op.f("ix_tickets_employee_id"), "tickets", ["employee_id"], unique=False)
    op.create_index(op.f("ix_tickets_assignee_id"), "tickets", ["assignee_id"], unique=False)
    op.create_index(op.f("ix_tickets_category"), "tickets", ["category"], unique=False)
    op.create_index(op.f("ix_tickets_priority"), "tickets", ["priority"], unique=False)
    op.create_index(op.f("ix_tickets_status"), "tickets", ["status"], unique=False)
    op.create_index(op.f("ix_tickets_created_at"), "tickets", ["created_at"], unique=False)

    op.create_table(
        "onboarding_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("task_name", sa.String(length=200), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_onboarding_tasks_id"), "onboarding_tasks", ["id"], unique=False)
    op.create_index(op.f("ix_onboarding_tasks_ticket_id"), "onboarding_tasks", ["ticket_id"], unique=False)
    op.create_index(op.f("ix_onboarding_tasks_is_completed"), "onboarding_tasks", ["is_completed"], unique=False)
    op.create_index(op.f("ix_onboarding_tasks_due_date"), "onboarding_tasks", ["due_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_onboarding_tasks_due_date"), table_name="onboarding_tasks")
    op.drop_index(op.f("ix_onboarding_tasks_is_completed"), table_name="onboarding_tasks")
    op.drop_index(op.f("ix_onboarding_tasks_ticket_id"), table_name="onboarding_tasks")
    op.drop_index(op.f("ix_onboarding_tasks_id"), table_name="onboarding_tasks")
    op.drop_table("onboarding_tasks")

    op.drop_index(op.f("ix_tickets_created_at"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_status"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_priority"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_category"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_assignee_id"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_employee_id"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_id"), table_name="tickets")
    op.drop_table("tickets")

