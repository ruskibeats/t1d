import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

from alembic import context

from app.db.models import Base

# Load .env file for DATABASE_URL
load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url with DATABASE_URL from .env if set.
# Alembic runs DDL synchronously, so we strip the async driver
# suffix to use the sync psycopg2 driver instead of asyncpg.
database_url = os.getenv("DATABASE_URL")
if database_url:
    sync_url = database_url.replace("+asyncpg", "").replace("+aiosqlite", "")
    config.set_main_option("sqlalchemy.url", sync_url)

# Also convert the .ini default if it uses an async driver
ini_url = config.get_main_option("sqlalchemy.url")
if ini_url:
    config.set_main_option(
        "sqlalchemy.url",
        ini_url.replace("+asyncpg", "").replace("+aiosqlite", ""),
    )

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using a sync connection.

    Alembic runs DDL statements which don't benefit from async.
    Using a sync engine avoids the greenlet dependency needed by
    asyncpg's sync-compatibility layer.
    """
    url = config.get_main_option("sqlalchemy.url")
    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
