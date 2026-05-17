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
    # Patch Operations to be idempotent so the squashed baseline (20260517_0000)
    # can pre-create all tables and the migration chain skips already-present DDL.
    #
    # Uses direct SQL queries (NOT sa.inspect) because Inspector caches its
    # results on the Connection object and returns stale data for schema objects
    # created earlier in the same transaction.
    #
    # Also patches NamedType._on_table_create to force checkfirst=True for
    # PostgreSQL ENUM types — the baseline creates all current-model enums, and
    # subsequent migrations that create historical tables using the same enum
    # types would otherwise raise DuplicateObjectError.
    from alembic.operations import Operations
    try:
        from sqlalchemy.dialects.postgresql.named_types import NamedType as _PgNamedType
        _orig_nt_otc = _PgNamedType._on_table_create

        def _on_table_create(self, target, bind, checkfirst: bool = False, **kw):
            return _orig_nt_otc(self, target, bind, checkfirst=True, **kw)

        _PgNamedType._on_table_create = _on_table_create
        _have_pg_patch = True
    except (ImportError, AttributeError):
        _have_pg_patch = False

    def _exists(sql: str, **params) -> bool:
        return bool(connection.execute(sa.text(sql), params).scalar())

    def _has_table(t: str) -> bool:
        return _exists(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name=:t)",
            t=t,
        )

    def _has_column(t: str, c: str) -> bool:
        return _exists(
            "SELECT EXISTS(SELECT 1 FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=:t AND column_name=:c)",
            t=t, c=c,
        )

    def _has_index(n: str) -> bool:
        return _exists(
            "SELECT EXISTS(SELECT 1 FROM pg_indexes "
            "WHERE schemaname='public' AND indexname=:n)",
            n=n,
        )

    def _has_fk(src: str, ref: str, local_cols) -> bool:
        """True if a FK from src→ref with exactly these local columns exists."""
        cols = [c for c in local_cols if isinstance(c, str)]
        if not cols:
            return False
        # Inline the column names as a SQL ARRAY literal — SQLAlchemy text() does
        # not parse :name as a parameter when immediately followed by ::type, so
        # we cannot use ANY(:cols::text[]).  Column names come from migration source
        # code (not user input), so literal inlining is safe.
        cols_literal = "ARRAY[" + ",".join(f"'{c}'" for c in cols) + "]"
        return _exists(
            "SELECT EXISTS("
            "  SELECT 1 FROM pg_constraint c"
            "  JOIN pg_class cs ON cs.oid = c.conrelid"
            "  JOIN pg_class cr ON cr.oid = c.confrelid"
            "  JOIN pg_namespace n ON n.oid = cs.relnamespace"
            "  WHERE c.contype = 'f'"
            "    AND n.nspname = 'public'"
            "    AND cs.relname = :src"
            "    AND cr.relname = :ref"
            "    AND array_length(c.conkey, 1) = :ncols"
            "    AND ("
            "      SELECT COUNT(*) FROM pg_attribute a"
            "      WHERE a.attrelid = cs.oid"
            "        AND a.attnum = ANY(c.conkey)"
            f"        AND a.attname = ANY({cols_literal})"
            "    ) = :ncols"
            ")",
            src=src, ref=ref, ncols=len(cols),
        )

    _orig_ct = Operations.create_table
    _orig_ac = Operations.add_column
    _orig_ci = Operations.create_index
    _orig_fk = Operations.create_foreign_key

    def _create_table(self, table_name: str, *cols, **kw):
        if _has_table(table_name):
            return None
        # Skip if any inline UniqueConstraint has a backing index that already
        # exists — happens when a table was renamed but the constraint name was
        # preserved (baseline creates the renamed table, migration creates the
        # old name with the same constraint, causing an index name collision).
        for item in cols:
            if isinstance(item, sa.UniqueConstraint) and item.name and _has_index(item.name):
                return None
        return _orig_ct(self, table_name, *cols, **kw)

    def _add_column(self, table_name: str, column, **kw):
        if _has_table(table_name) and _has_column(table_name, column.name):
            return
        return _orig_ac(self, table_name, column, **kw)

    def _create_index(self, index_name, table_name: str, columns, **kw):
        name_str = str(index_name) if index_name is not None else None
        if not _has_table(table_name):
            # Table doesn't exist — either create_table was skipped (renamed/removed
            # table) or this index precedes the table in the migration (bug). In both
            # cases we cannot create the index; skip to avoid UndefinedTableError.
            return None
        if name_str and _has_index(name_str):
            return None
        # Skip if any plain-string column doesn't exist (removed from current model —
        # baseline created the table without it because it's no longer in the model).
        for col in columns:
            if isinstance(col, str) and not _has_column(table_name, col):
                return None
        return _orig_ci(self, index_name, table_name, columns, **kw)

    def _create_foreign_key(self, constraint_name, source_table: str,
                             referent_table: str, local_cols, remote_cols, **kw):
        if not _has_table(source_table):
            # Source table doesn't exist (create_table was skipped); skip the FK too.
            return None
        if _has_fk(source_table, referent_table, local_cols):
            return None
        # Skip if any local column doesn't exist (removed from current model).
        for col in local_cols:
            if isinstance(col, str) and not _has_column(source_table, col):
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
        if _have_pg_patch:
            _PgNamedType._on_table_create = _orig_nt_otc


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
