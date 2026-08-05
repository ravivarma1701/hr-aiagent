"""employee documents uploaded_by

Revision ID: 0016_employee_documents_uploaded_by
Revises: 0015_half_day_leave_support
Create Date: 2026-03-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0016_employee_documents_uploaded_by"
down_revision: Union[str, None] = "0015_half_day_leave_support"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        with op.batch_alter_table("employee_documents") as batch_op:
            batch_op.add_column(sa.Column("uploaded_by", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_employee_documents_uploaded_by",
                "employees",
                ["uploaded_by"],
                ["id"],
            )
            batch_op.create_index("ix_employee_documents_uploaded_by", ["uploaded_by"], unique=False)
    else:
        op.add_column("employee_documents", sa.Column("uploaded_by", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_employee_documents_uploaded_by",
            "employee_documents",
            "employees",
            ["uploaded_by"],
            ["id"],
        )
        op.create_index("ix_employee_documents_uploaded_by", "employee_documents", ["uploaded_by"], unique=False)

    # Backfill legacy rows as self-uploaded when uploader is unknown.
    op.execute("UPDATE employee_documents SET uploaded_by = employee_id WHERE uploaded_by IS NULL")


def downgrade() -> None:
    op.drop_index("ix_employee_documents_uploaded_by", table_name="employee_documents")
    op.drop_constraint("fk_employee_documents_uploaded_by", "employee_documents", type_="foreignkey")
    op.drop_column("employee_documents", "uploaded_by")
