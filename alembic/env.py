"""
Alembic environment configuration.

Alembic calls this file to configure the migration environment.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
# Import SQLModel and app config
from sqlmodel import SQLModel

from app.core.config import settings
# Import all models so Alembic can detect schema changes
from app.db.base import *  # noqa

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set SQLAlchemy URL from settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Metadata for autogenerate support
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This configures the context with just a URL and not an Engine.
    Calls to context.execute() emit the given string to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={ "paramstyle": "named" }, )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    
    Create an Engine and associate a connection with the context.
    """
    connectable = engine_from_config(config.get_section(config.config_ini_section, { }), prefix="sqlalchemy.",
                                     poolclass=pool.NullPool, )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


# Run migrations
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
