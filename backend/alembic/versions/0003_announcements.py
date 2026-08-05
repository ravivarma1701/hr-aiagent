"""announcements schema

Revision ID: 0003_announcements
Revises: 0002_leave_workflow
Create Date: 2026-02-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_announcements"
down_revision: Union[str, None] = "0002_leave_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "announcements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_announcements_id"), "announcements", ["id"], unique=False)
    op.create_index(op.f("ix_announcements_title"), "announcements", ["title"], unique=False)
    op.create_index(op.f("ix_announcements_author_id"), "announcements", ["author_id"], unique=False)
    op.create_index(op.f("ix_announcements_created_at"), "announcements", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_announcements_created_at"), table_name="announcements")
    op.drop_index(op.f("ix_announcements_author_id"), table_name="announcements")
    op.drop_index(op.f("ix_announcements_title"), table_name="announcements")
    op.drop_index(op.f("ix_announcements_id"), table_name="announcements")
    op.drop_table("announcements")
