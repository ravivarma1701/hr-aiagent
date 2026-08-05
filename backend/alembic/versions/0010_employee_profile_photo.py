"""employee profile photo fields

Revision ID: 0010_employee_profile_photo
Revises: 0009_hr_policy_file_meta
Create Date: 2026-03-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_employee_profile_photo"
down_revision: Union[str, None] = "0009_hr_policy_file_meta"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("profile_photo_path", sa.String(length=255), nullable=True))
    op.add_column("employees", sa.Column("profile_photo_mime", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("employees", "profile_photo_mime")
    op.drop_column("employees", "profile_photo_path")
