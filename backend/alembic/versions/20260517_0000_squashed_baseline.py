"""squashed baseline — creates all tables for fresh-DB initialisation via alembic upgrade head.

The migration chain was added after many tables already existed in production.
This baseline runs first (down_revision=None) and creates every table defined in
the current SQLAlchemy models with checkfirst=True, so that subsequent migrations
in the chain safely add only the columns/indexes/FKs that don't exist yet.

env.py patches the four mutable Operations methods (create_table, add_column,
create_index, create_foreign_key) to be idempotent, so the chain can run in
full on a fresh DB without any "already exists" errors.

Revision ID: 20260517_0000
Revises:
Create Date: 2026-05-17
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260517_0000"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import text

    from app.db.base import Base
    import app.models  # noqa: F401

    bind = op.get_bind()
    bind.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    raise NotImplementedError(
        "Cannot downgrade the squashed baseline. "
        "To reset a dev DB: docker compose --env-file .env.development down -v && "
        "docker compose --env-file .env.development up -d"
    )
