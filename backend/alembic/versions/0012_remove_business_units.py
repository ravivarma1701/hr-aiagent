"""remove business units table

Revision ID: 0012_remove_business_units
Revises: 0011_employee_finance_profile
Create Date: 2026-03-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0012_remove_business_units"
down_revision: Union[str, None] = "0011_employee_finance_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    op.execute("DROP INDEX IF EXISTS ix_departments_business_unit_id")
    if dialect == "sqlite":
        with op.batch_alter_table("departments") as batch_op:
            batch_op.drop_column("business_unit_id")
        op.execute("DROP TABLE IF EXISTS business_units")
    else:
        op.execute("ALTER TABLE departments DROP COLUMN IF EXISTS business_unit_id")
        op.execute("DROP TABLE IF EXISTS business_units CASCADE")


def downgrade() -> None:
    op.create_table(
        "business_units",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("head_employee_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["head_employee_id"],
            ["employees.id"],
            name="fk_business_units_head_employee_id_employees",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_business_units_id", "business_units", ["id"], unique=False)
    op.add_column("departments", sa.Column("business_unit_id", sa.Integer(), nullable=True))
    op.create_index("ix_departments_business_unit_id", "departments", ["business_unit_id"], unique=False)
    op.create_foreign_key(
        "departments_business_unit_id_fkey",
        "departments",
        "business_units",
        ["business_unit_id"],
        ["id"],
    )
    op.execute("UPDATE departments SET business_unit_id = (SELECT id FROM business_units ORDER BY id LIMIT 1)")
    op.alter_column("departments", "business_unit_id", existing_type=sa.Integer(), nullable=False)
