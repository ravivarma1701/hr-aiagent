"""employee finance and pan profile fields

Revision ID: 0011_employee_finance_profile
Revises: 0010_employee_profile_photo
Create Date: 2026-03-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011_employee_finance_profile"
down_revision: Union[str, None] = "0010_employee_profile_photo"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("current_salary_usd", sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column("employees", sa.Column("bank_name", sa.String(length=120), nullable=True))
    op.add_column("employees", sa.Column("bank_account_number", sa.String(length=34), nullable=True))
    op.add_column("employees", sa.Column("bank_account_name", sa.String(length=120), nullable=True))
    op.add_column("employees", sa.Column("bank_branch", sa.String(length=120), nullable=True))
    op.add_column("employees", sa.Column("bank_ifsc", sa.String(length=20), nullable=True))
    op.add_column("employees", sa.Column("pan_number", sa.String(length=20), nullable=True))
    op.add_column("employees", sa.Column("pan_name", sa.String(length=120), nullable=True))
    op.add_column("employees", sa.Column("pan_dob", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("employees", "pan_dob")
    op.drop_column("employees", "pan_name")
    op.drop_column("employees", "pan_number")
    op.drop_column("employees", "bank_ifsc")
    op.drop_column("employees", "bank_branch")
    op.drop_column("employees", "bank_account_name")
    op.drop_column("employees", "bank_account_number")
    op.drop_column("employees", "bank_name")
    op.drop_column("employees", "current_salary_usd")
