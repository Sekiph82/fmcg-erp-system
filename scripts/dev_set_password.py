"""LOCAL development only: set the password of a synthetic test user (staff, distributor or supplier) for device testing.

Usage (from the repository root, dev stack running):
    docker compose exec backend python /app/../scripts/dev_set_password.py  -- not available inside the container, use:
    docker cp scripts/dev_set_password.py fmcg-erp-system-backend-1:/tmp/p.py
    docker compose exec -e PYTHONPATH=/app backend python /tmp/p.py synth-field
The password is asked for interactively and never printed. Refuses to run unless ENVIRONMENT is development.
"""
import asyncio
import getpass
import os
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal


async def main(login: str) -> None:
    if os.environ.get("ENVIRONMENT", "development").lower() != "development":
        raise SystemExit("Refusing: only for the local development stack.")
    from app.models.portal import PortalUser
    from app.models.supplier_portal import SPUser
    from app.models.user import User

    pw = getpass.getpass(f"New password for {login}: ")
    if len(pw) < 10 or pw != getpass.getpass("Repeat: "):
        raise SystemExit("Passwords differ or shorter than 10 characters.")
    async with AsyncSessionLocal() as db:
        for model, col, attr in ((User, User.username, "hashed_password"), (PortalUser, PortalUser.email, "password_hash"),
                                 (SPUser, SPUser.email, "password_hash")):
            row = (await db.execute(select(model).where(col == login))).scalar_one_or_none()
            if row is not None:
                if not (getattr(row, "username", "") or getattr(row, "email", "")).startswith("synth-"):
                    raise SystemExit("Only synthetic test accounts (synth-...) can be changed with this script.")
                setattr(row, attr, hash_password(pw))
                await db.commit()
                print(f"Password set for {login}.")
                return
    raise SystemExit(f"No user {login}.")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else input("Login (e.g. synth-field): ").strip()))
