"""add project status column

Revision ID: 0014_project_status
Revises: 0013_employee_documents
Create Date: 2026-03-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0014_project_status"
down_revision: Union[str, None] = "0013_employee_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="ONGOING",
        ),
    )
    op.create_index(op.f("ix_projects_status"), "projects", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_projects_status"), table_name="projects")
    op.drop_column("projects", "status")
