import asyncio
from logging.config import fileConfig

import sqlalchemy as sa
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.core.config import settings
from app.db.base import Base
import app.models  # noqa: F401 – register all models with Base.metadata

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    # Patch the four mutable Operations methods to be idempotent so that the
    # squashed baseline (20260517_0000) can create all tables up-front and the
    # remaining migration chain skips DDL that is already in place.
    from alembic.operations import Operations

    _orig_ct = Operations.create_table
    _orig_ac = Operations.add_column
    _orig_ci = Operations.create_index
    _orig_fk = Operations.create_foreign_key

    def _create_table(self, table_name: str, *cols, **kw):
        if sa.inspect(connection).has_table(table_name):
            return None
        return _orig_ct(self, table_name, *cols, **kw)

    def _add_column(self, table_name: str, column, **kw):
        insp = sa.inspect(connection)
        if insp.has_table(table_name):
            if column.name in {c["name"] for c in insp.get_columns(table_name)}:
                return
        return _orig_ac(self, table_name, column, **kw)

    def _create_index(self, index_name, table_name: str, columns, **kw):
        name_str = str(index_name) if index_name is not None else None
        insp = sa.inspect(connection)
        if name_str and insp.has_table(table_name):
            if name_str in {i["name"] for i in insp.get_indexes(table_name)}:
                return None
        return _orig_ci(self, index_name, table_name, columns, **kw)

    def _create_foreign_key(self, constraint_name, source_table: str,
                             referent_table: str, local_cols, remote_cols, **kw):
        insp = sa.inspect(connection)
        if insp.has_table(source_table):
            for fk in insp.get_foreign_keys(source_table):
                if (fk["referred_table"] == referent_table and
                        set(fk["constrained_columns"]) == set(local_cols)):
                    return None
        return _orig_fk(self, constraint_name, source_table, referent_table,
                        local_cols, remote_cols, **kw)

    Operations.create_table = _create_table
    Operations.add_column = _add_column
    Operations.create_index = _create_index
    Operations.create_foreign_key = _create_foreign_key

    try:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    finally:
        Operations.create_table = _orig_ct
        Operations.add_column = _orig_ac
        Operations.create_index = _orig_ci
        Operations.create_foreign_key = _orig_fk


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
