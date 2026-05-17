"""
Development database initialization script.

Invoked by the Docker dev container CMD before uvicorn:
    python scripts/dev_migrate.py && uvicorn app.main:app ...

Behavior:

  production:
    - Always runs ``alembic upgrade head``. Fails loudly on error.
    - Never falls back to create_all.

  development (default):
    - Fresh DB (no public tables):
        1. Enable uuid-ossp extension.
        2. ``Base.metadata.create_all()`` — creates all tables from current models.
        3. ``alembic stamp head`` — marks all migrations as applied.
        !! DEV ONLY !! Production MUST use ``alembic upgrade head``.

    - Existing DB with Alembic version table:
        ``alembic upgrade head`` — applies pending incremental migrations.

    - Existing DB without Alembic tracking (prior create_all bootstrap):
        1. Reconcile known schema drift columns.
        2. ``alembic stamp head`` — marks baseline applied.
        (Incremental migrations from this point forward will run normally.)

WHY NOT PURE ALEMBIC ON A FRESH DB?
  The migration chain begins with 3c45d9071c98 which adds columns to
  ``sales_orders`` — a table the chain never creates.  All subsequent
  migrations reference ``users``, ``suppliers``, ``products``, etc. via FK.
  Pure ``alembic upgrade head`` on a fresh database will fail immediately.
  The base schema must be bootstrapped via ``create_all()`` first.
  This is a known design constraint: Alembic was introduced after the initial
  schema was already deployed.  Only use ``alembic upgrade head`` in production
  when the schema already exists.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.db.base import Base
import app.models  # noqa: F401 — registers ALL models with Base.metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dev_migrate")


def _alembic_config() -> Config:
    return Config(str(ROOT / "alembic.ini"))


async def _count_public_tables() -> int:
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                )
            )
            return int(result.scalar() or 0)
    finally:
        await engine.dispose()


async def _has_alembic_version_table() -> bool:
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'alembic_version')"
                )
            )
            return bool(result.scalar())
    finally:
        await engine.dispose()


async def _exists(table_name: str) -> bool:
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = :t)"
                ),
                {"t": table_name},
            )
            return bool(result.scalar())
    finally:
        await engine.dispose()


async def _create_all_tables() -> None:
    """DEV ONLY: bootstrap full schema from current SQLAlchemy models."""
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.begin() as conn:
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            await conn.run_sync(Base.metadata.create_all)
            logger.info("DEV ONLY: schema created from SQLAlchemy models")
    finally:
        await engine.dispose()


async def _ensure_reconciliation_columns() -> None:
    """
    Apply known schema drift between create_all and the Alembic history.
    Called only when reconciling an existing non-tracked create_all database.
    """
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.begin() as conn:
            # Added by migration 20260510_0700_user_must_change_password
            await conn.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN IF NOT EXISTS must_change_password "
                    "BOOLEAN NOT NULL DEFAULT false"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE users "
                    "ALTER COLUMN must_change_password DROP DEFAULT"
                )
            )
    finally:
        await engine.dispose()


def main() -> None:
    config = _alembic_config()
    is_production = settings.ENVIRONMENT.lower() == "production"

    # ── Production: always Alembic, no fallback ───────────────────────────────
    if is_production:
        logger.info("Production: running alembic upgrade head")
        command.upgrade(config, "head")
        logger.info("Alembic migrations applied")
        return

    # ── Development ───────────────────────────────────────────────────────────
    table_count = asyncio.run(_count_public_tables())
    has_alembic = asyncio.run(_has_alembic_version_table())

    if table_count == 0:
        # Fresh database
        logger.warning(
            "DEV ONLY: fresh database — creating schema from SQLAlchemy models "
            "and stamping Alembic head. "
            "Production MUST use 'alembic upgrade head'."
        )
        asyncio.run(_create_all_tables())
        command.stamp(config, "head")
        logger.info("Dev baseline schema created and stamped to head")
        return

    if has_alembic:
        # Existing Alembic-tracked database — upgrade normally
        logger.info("Alembic version table found — running upgrade head")
        command.upgrade(config, "head")
        logger.info("Alembic upgrade complete")
        return

    # Existing create_all database without Alembic tracking
    has_users = asyncio.run(_exists("users"))
    has_late_schema = asyncio.run(_exists("crm_pipeline_stages"))
    if not (has_users and has_late_schema):
        raise RuntimeError(
            "Database has tables but is not a recognisable dev schema "
            "(missing 'users' or 'crm_pipeline_stages'). "
            "Manual intervention required — back up data then run: "
            "docker compose --env-file .env.development down -v"
        )

    logger.warning(
        "DEV ONLY: detected create_all schema without Alembic tracking. "
        "Reconciling drift columns and stamping head."
    )
    asyncio.run(_ensure_reconciliation_columns())
    command.stamp(config, "head")
    logger.info("Dev schema reconciled and stamped to Alembic head")


if __name__ == "__main__":
    main()
