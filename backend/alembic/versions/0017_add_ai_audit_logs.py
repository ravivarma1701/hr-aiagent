"""add ai_audit_logs table

Revision ID: 0017_add_ai_audit_logs
Revises: 0016_employee_documents_uploaded_by
Create Date: 2026-08-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0017_add_ai_audit_logs"
down_revision: Union[str, None] = "0016_employee_documents_uploaded_by"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(length=50), nullable=True),
        sa.Column("tool_name", sa.String(length=100), nullable=True),
        sa.Column("action_status", sa.String(length=30), nullable=False),
        sa.Column("records_accessed", sa.Text(), nullable=True),
        sa.Column("error_reason", sa.String(length=255), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_ai_audit_logs_user_id", "ai_audit_logs", ["user_id"])
    op.create_index("ix_ai_audit_logs_intent", "ai_audit_logs", ["intent"])
    op.create_index("ix_ai_audit_logs_tool_name", "ai_audit_logs", ["tool_name"])
    op.create_index("ix_ai_audit_logs_action_status", "ai_audit_logs", ["action_status"])
    op.create_index("ix_ai_audit_logs_created_at", "ai_audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_audit_logs_created_at", table_name="ai_audit_logs")
    op.drop_index("ix_ai_audit_logs_action_status", table_name="ai_audit_logs")
    op.drop_index("ix_ai_audit_logs_tool_name", table_name="ai_audit_logs")
    op.drop_index("ix_ai_audit_logs_intent", table_name="ai_audit_logs")
    op.drop_index("ix_ai_audit_logs_user_id", table_name="ai_audit_logs")
    op.drop_table("ai_audit_logs")
