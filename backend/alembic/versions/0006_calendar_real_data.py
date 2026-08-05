"""calendar real data schema

Revision ID: 0006_calendar_real_data
Revises: 0005_phase3_ai
Create Date: 2026-02-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_calendar_real_data"
down_revision: Union[str, None] = "0005_phase3_ai"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.create_index(op.f("ix_employees_date_of_birth"), "employees", ["date_of_birth"], unique=False)

    op.create_table(
        "holidays",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_holidays_id"), "holidays", ["id"], unique=False)
    op.create_index(op.f("ix_holidays_name"), "holidays", ["name"], unique=False)
    op.create_index(op.f("ix_holidays_date"), "holidays", ["date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_holidays_date"), table_name="holidays")
    op.drop_index(op.f("ix_holidays_name"), table_name="holidays")
    op.drop_index(op.f("ix_holidays_id"), table_name="holidays")
    op.drop_table("holidays")

    op.drop_index(op.f("ix_employees_date_of_birth"), table_name="employees")
    op.drop_column("employees", "date_of_birth")
