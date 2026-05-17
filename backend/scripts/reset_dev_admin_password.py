"""
DEV ONLY — manually reset the local admin password from current .env.development values.

Usage (inside Docker):
    docker compose --env-file .env.development exec backend python scripts/reset_dev_admin_password.py

Refuses to run in production.
Never prints the actual password.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
import app.models  # noqa: F401 — registers all models

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("reset_dev_admin")


async def reset() -> None:
    from app.models.user import User, user_role
    from app.models.role import Role

    if settings.ENVIRONMENT.lower() == "production":
        logger.error("This script must not be run in production.")
        sys.exit(1)

    username = settings.INITIAL_ADMIN_USERNAME
    password = settings.INITIAL_ADMIN_PASSWORD

    if not username:
        logger.error("INITIAL_ADMIN_USERNAME is not set.")
        sys.exit(1)
    if not password:
        logger.error("INITIAL_ADMIN_PASSWORD is not set in .env.development.")
        sys.exit(1)

    engine = create_async_engine(settings.DATABASE_URL)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if user is None:
            # Create fresh admin
            owner_result = await db.execute(select(Role).where(Role.name == "owner"))
            owner_role = owner_result.scalar_one_or_none()

            user = User(
                email=settings.INITIAL_ADMIN_EMAIL,
                username=username,
                full_name=settings.INITIAL_ADMIN_FULL_NAME,
                hashed_password=hash_password(password),
                is_active=True,
                is_superuser=True,
                must_change_password=False,
            )
            db.add(user)
            await db.flush()

            if owner_role:
                await db.execute(
                    insert(user_role).values(user_id=user.id, role_id=owner_role.id)
                )

            await db.commit()
            print(f"\nDevelopment admin CREATED successfully.")
            print(f"  username : {username}")
            print(f"  email    : {settings.INITIAL_ADMIN_EMAIL}")
            print(f"  password : (from INITIAL_ADMIN_PASSWORD in .env.development)")
            print()
        else:
            # Update existing admin
            user.hashed_password = hash_password(password)
            user.is_active = True
            user.is_superuser = True
            user.must_change_password = False

            # Ensure owner role is assigned
            role_check = await db.execute(
                select(user_role).where(user_role.c.user_id == user.id)
            )
            if not role_check.fetchone():
                owner_result = await db.execute(select(Role).where(Role.name == "owner"))
                owner_role = owner_result.scalar_one_or_none()
                if owner_role:
                    await db.execute(
                        insert(user_role).values(user_id=user.id, role_id=owner_role.id)
                    )

            await db.commit()
            print(f"\nDevelopment admin password RESET successfully.")
            print(f"  username : {username}")
            print(f"  password : (from INITIAL_ADMIN_PASSWORD in .env.development)")
            print()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(reset())
