"""Alembic env.py для AI AutoClip Pro 2.0.

Читает URL БД из переменной окружения DATABASE_URL (или дефолтный SQLite),
подключается к метаданным src.database.models и поддерживает авто-генерацию
миграций командой:

    alembic revision --autogenerate -m "message"
"""
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Импортируем Base и модели, чтобы метаданные содержали все таблицы.
from src.database.base import Base
import src.database.models  # noqa: F401  (регистрация моделей)

# this is the Alembic Config object, which provides access to the .ini file
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Берём URL из окружения, иначе fallback из alembic.ini.
db_url = os.getenv("DATABASE_URL", "").strip()
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL, no DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # важно для SQLite ALTER TABLE
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connect to DB)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # важно для SQLite ALTER TABLE
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()