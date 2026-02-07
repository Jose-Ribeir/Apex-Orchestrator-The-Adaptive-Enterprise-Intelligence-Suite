"""
Alembic env.py: use DATABASE_URL from app config.
Run migrations from the python/ directory: alembic upgrade head
"""

import sys
from pathlib import Path

# Ensure app is importable when running: alembic upgrade head (from python/)
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# Import app config and (when you add models) metadata for autogenerate
from app.config import get_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# URL from .env (DATABASE_URL)
settings = get_settings()
if not settings.database_configured:
    raise RuntimeError("Database not configured. Set DATABASE_URL in .env before running migrations.")
database_url = settings.get_database_url()
# Do not set_main_option(): ConfigParser treats % in the URL (e.g. %7D) as interpolation and raises.

# For autogenerate: use models' metadata
from app.models import Base

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (SQL only, no DB connection)."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (with DB connection)."""
    connectable = create_engine(
        database_url,
        poolclass=pool.NullPool,
        connect_args={"connect_timeout": 10},
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
