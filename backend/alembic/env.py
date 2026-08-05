from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db.base import Base
from app.models import (
    announcement,
    attendance_log,
    department,
    employee,
    employee_document,
    hr_policy,
    job_history,
    leave_balance,
    leave_request,
    onboarding_task,
    payroll_record,
    poll,
    poll_response,
    ticket,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _sync_db_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./storage/hrms.db")
    return url.replace("+aiosqlite", "")


config.set_main_option("sqlalchemy.url", _sync_db_url())
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
