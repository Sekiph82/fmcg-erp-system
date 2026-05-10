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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dev_migrate")


def _alembic_config() -> Config:
    return Config(str(ROOT / "alembic.ini"))


async def _exists(table_name: str) -> bool:
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = :table_name
                    )
                    """
                ),
                {"table_name": table_name},
            )
            return bool(result.scalar())
    finally:
        await engine.dispose()


async def _ensure_dev_reconciliation_columns() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT false
                    """
                )
            )
            await conn.execute(
                text("ALTER TABLE users ALTER COLUMN must_change_password DROP DEFAULT")
            )
    finally:
        await engine.dispose()


def main() -> None:
    config = _alembic_config()
    try:
        command.upgrade(config, "head")
        return
    except Exception:
        if settings.ENVIRONMENT != "development":
            raise
        logger.exception("Alembic upgrade failed; checking for create_all development schema drift")

    has_users = asyncio.run(_exists("users"))
    has_late_schema = asyncio.run(_exists("crm_pipeline_stages"))
    if not (has_users and has_late_schema):
        raise RuntimeError("Alembic upgrade failed and database does not look like an existing create_all dev schema")

    logger.warning("Detected existing development schema created outside Alembic; reconciling and stamping head")
    asyncio.run(_ensure_dev_reconciliation_columns())
    command.stamp(config, "head")
    logger.info("Development database reconciled and stamped to Alembic head")


if __name__ == "__main__":
    main()
