"""employee documents storage

Revision ID: 0013_employee_documents
Revises: 0012_remove_business_units
Create Date: 2026-03-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0013_employee_documents"
down_revision: Union[str, None] = "0012_remove_business_units"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("document_type", sa.String(length=40), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_employee_documents_id"), "employee_documents", ["id"], unique=False)
    op.create_index(op.f("ix_employee_documents_employee_id"), "employee_documents", ["employee_id"], unique=False)
    op.create_index(op.f("ix_employee_documents_document_type"), "employee_documents", ["document_type"], unique=False)
    op.create_index(op.f("ix_employee_documents_checksum"), "employee_documents", ["checksum"], unique=False)
    op.create_index(op.f("ix_employee_documents_created_at"), "employee_documents", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_employee_documents_created_at"), table_name="employee_documents")
    op.drop_index(op.f("ix_employee_documents_checksum"), table_name="employee_documents")
    op.drop_index(op.f("ix_employee_documents_document_type"), table_name="employee_documents")
    op.drop_index(op.f("ix_employee_documents_employee_id"), table_name="employee_documents")
    op.drop_index(op.f("ix_employee_documents_id"), table_name="employee_documents")
    op.drop_table("employee_documents")
