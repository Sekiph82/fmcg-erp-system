"""
Production first-deploy bootstrap script.

USE ONLY ON A COMPLETELY FRESH PRODUCTION DATABASE — RUN EXACTLY ONCE.

This script exists because the Alembic migration chain cannot be applied to a fresh
database: the initial migration (3c45d9071c98) only adds columns to existing tables,
never creates them. Pure `alembic upgrade head` fails immediately on an empty DB.

This script bridges that gap:
  1. Asserts the database is completely empty (refuses if any tables exist).
  2. Creates all tables from the current SQLAlchemy models (create_all).
  3. Stamps Alembic at the current head so future incremental migrations work.
  4. Exits with code 0 on success, code 1 on any failure.

USAGE:
  BOOTSTRAP_PRODUCTION=true python scripts/prod_bootstrap.py

GUARDS:
  - Requires BOOTSTRAP_PRODUCTION=true in the environment.
  - Requires ENVIRONMENT=production.
  - Aborts if any public table already exists (prevents double-bootstrap).

AFTER THIS RUNS:
  - Run `alembic upgrade head` to verify it is a no-op (it should be).
  - Start the application normally.
  - Never run this script again on this database.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.db.base import Base
import app.models  # noqa: F401 — registers ALL models with Base.metadata

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("prod_bootstrap")


def _alembic_config() -> Config:
    return Config(str(ROOT / "alembic.ini"))


async def _count_public_tables(engine) -> int:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
        )
        return int(result.scalar() or 0)


async def _bootstrap(engine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.run_sync(Base.metadata.create_all)


async def run() -> None:
    guard = os.environ.get("BOOTSTRAP_PRODUCTION", "").lower()
    if guard != "true":
        logger.error(
            "ABORT: BOOTSTRAP_PRODUCTION env var not set to 'true'. "
            "This script requires explicit opt-in: BOOTSTRAP_PRODUCTION=true python scripts/prod_bootstrap.py"
        )
        sys.exit(1)

    if settings.ENVIRONMENT.lower() != "production":
        logger.error(
            "ABORT: ENVIRONMENT is '%s', not 'production'. "
            "This script is only for production databases.",
            settings.ENVIRONMENT,
        )
        sys.exit(1)

    logger.warning("=" * 72)
    logger.warning("PRODUCTION BOOTSTRAP — creating schema from SQLAlchemy models")
    logger.warning("Run this ONLY on the first deploy with a completely empty database.")
    logger.warning("=" * 72)

    engine = create_async_engine(settings.DATABASE_URL)
    try:
        table_count = await _count_public_tables(engine)

        if table_count > 0:
            logger.error(
                "ABORT: Database already has %d public tables. "
                "prod_bootstrap.py must only run on a completely empty database. "
                "If this is intentional, run 'alembic upgrade head' instead.",
                table_count,
            )
            sys.exit(1)

        logger.info("Database is empty — creating all tables from models...")
        await _bootstrap(engine)
        logger.info("Schema created successfully.")

    finally:
        await engine.dispose()

    config = _alembic_config()
    command.stamp(config, "head")
    logger.info("Alembic stamped to head.")

    logger.warning("=" * 72)
    logger.warning("Bootstrap complete.")
    logger.warning("NEXT STEPS:")
    logger.warning("  1. Run: alembic upgrade head  (should be a no-op)")
    logger.warning("  2. Start the application: docker compose -f docker-compose.prod.yml up -d")
    logger.warning("  3. Never run this script on this database again.")
    logger.warning("=" * 72)


if __name__ == "__main__":
    asyncio.run(run())
