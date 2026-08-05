"""half day leave support

Revision ID: 0015_half_day_leave_support
Revises: 0014_project_status
Create Date: 2026-03-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0015_half_day_leave_support"
down_revision: Union[str, None] = "0014_project_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("leave_requests") as batch_op:
        batch_op.add_column(sa.Column("is_half_day", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(
            sa.Column(
                "half_day_period",
                sa.Enum("FIRST_HALF", "SECOND_HALF", name="halfdayperiod", native_enum=False),
                nullable=True,
            )
        )

    with op.batch_alter_table("leave_balances") as batch_op:
        batch_op.alter_column("total", existing_type=sa.Integer(), type_=sa.Float(), existing_nullable=False)
        batch_op.alter_column("used", existing_type=sa.Integer(), type_=sa.Float(), existing_nullable=False)
        batch_op.alter_column("remaining", existing_type=sa.Integer(), type_=sa.Float(), existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("leave_balances") as batch_op:
        batch_op.alter_column("remaining", existing_type=sa.Float(), type_=sa.Integer(), existing_nullable=False)
        batch_op.alter_column("used", existing_type=sa.Float(), type_=sa.Integer(), existing_nullable=False)
        batch_op.alter_column("total", existing_type=sa.Float(), type_=sa.Integer(), existing_nullable=False)

    with op.batch_alter_table("leave_requests") as batch_op:
        batch_op.drop_column("half_day_period")
        batch_op.drop_column("is_half_day")
