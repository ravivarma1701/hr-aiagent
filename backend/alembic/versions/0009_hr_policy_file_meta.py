"""hr policy metadata for filesystem storage

Revision ID: 0009_hr_policy_file_meta
Revises: 0008_skills_projects_reco
Create Date: 2026-03-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009_hr_policy_file_meta"
down_revision: Union[str, None] = "0008_skills_projects_reco"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        with op.batch_alter_table("hr_policies") as batch_op:
            batch_op.alter_column("content", existing_type=sa.Text(), nullable=True)
            batch_op.add_column(sa.Column("original_filename", sa.String(length=255), nullable=True))
            batch_op.add_column(sa.Column("file_path", sa.Text(), nullable=True))
            batch_op.add_column(sa.Column("mime_type", sa.String(length=100), nullable=True))
            batch_op.add_column(sa.Column("size_bytes", sa.Integer(), nullable=True))
            batch_op.add_column(sa.Column("uploaded_by", sa.Integer(), nullable=True))
            batch_op.add_column(sa.Column("checksum", sa.String(length=64), nullable=True))
            batch_op.add_column(
                sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False)
            )
            batch_op.create_foreign_key("fk_hr_policies_uploaded_by", "employees", ["uploaded_by"], ["id"])
    else:
        op.alter_column("hr_policies", "content", existing_type=sa.Text(), nullable=True)
        op.add_column("hr_policies", sa.Column("original_filename", sa.String(length=255), nullable=True))
        op.add_column("hr_policies", sa.Column("file_path", sa.Text(), nullable=True))
        op.add_column("hr_policies", sa.Column("mime_type", sa.String(length=100), nullable=True))
        op.add_column("hr_policies", sa.Column("size_bytes", sa.Integer(), nullable=True))
        op.add_column("hr_policies", sa.Column("uploaded_by", sa.Integer(), nullable=True))
        op.add_column("hr_policies", sa.Column("checksum", sa.String(length=64), nullable=True))
        op.add_column(
            "hr_policies",
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        )
        op.create_foreign_key("fk_hr_policies_uploaded_by", "hr_policies", "employees", ["uploaded_by"], ["id"])
    op.create_index(op.f("ix_hr_policies_uploaded_by"), "hr_policies", ["uploaded_by"], unique=False)
    op.create_index(op.f("ix_hr_policies_checksum"), "hr_policies", ["checksum"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_hr_policies_checksum"), table_name="hr_policies")
    op.drop_index(op.f("ix_hr_policies_uploaded_by"), table_name="hr_policies")
    op.drop_constraint("fk_hr_policies_uploaded_by", "hr_policies", type_="foreignkey")
    op.drop_column("hr_policies", "created_at")
    op.drop_column("hr_policies", "checksum")
    op.drop_column("hr_policies", "uploaded_by")
    op.drop_column("hr_policies", "size_bytes")
    op.drop_column("hr_policies", "mime_type")
    op.drop_column("hr_policies", "file_path")
    op.drop_column("hr_policies", "original_filename")
    op.alter_column("hr_policies", "content", existing_type=sa.Text(), nullable=False)
