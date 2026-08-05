"""attendance mode and punctuality

Revision ID: 0007_attendance_mode_punctuality
Revises: 0006_calendar_real_data
Create Date: 2026-02-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_attendance_mode_punctuality"
down_revision: Union[str, None] = "0006_calendar_real_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("attendance_logs", sa.Column("work_mode", sa.String(length=20), nullable=True))
    op.add_column("attendance_logs", sa.Column("punctuality", sa.String(length=20), nullable=True))
    op.create_index(op.f("ix_attendance_logs_work_mode"), "attendance_logs", ["work_mode"], unique=False)
    op.create_index(op.f("ix_attendance_logs_punctuality"), "attendance_logs", ["punctuality"], unique=False)

    op.execute(
        """
        UPDATE attendance_logs
        SET
          work_mode = CASE
            WHEN status = 'WFH' THEN 'WFH'
            WHEN status = 'ABSENT' THEN 'ABSENT'
            ELSE 'PRESENT'
          END,
          punctuality = CASE
            WHEN status IN ('ON_TIME', 'LATE') THEN status
            ELSE NULL
          END
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_attendance_logs_punctuality"), table_name="attendance_logs")
    op.drop_index(op.f("ix_attendance_logs_work_mode"), table_name="attendance_logs")
    op.drop_column("attendance_logs", "punctuality")
    op.drop_column("attendance_logs", "work_mode")
