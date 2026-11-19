"""Supplier portal users get a one-time set-password token (stored as a SHA-256 digest) — M38.S01.T001."""

import sqlalchemy as sa
from alembic import op

revision = "20261119_0045"
down_revision = "20261119_0044"
branch_labels = None
depends_on = None


def _columns():
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("sp_users")}


def upgrade() -> None:
    cols = _columns()  # fresh databases already have them from the model-based baseline
    if "invitation_token" not in cols:
        op.add_column("sp_users", sa.Column("invitation_token", sa.String(64), nullable=True))
        op.create_index("ix_sp_users_invitation_token", "sp_users", ["invitation_token"])
    if "token_expires_at" not in cols:
        op.add_column("sp_users", sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    cols = _columns()
    if "invitation_token" in cols:
        op.drop_index("ix_sp_users_invitation_token", table_name="sp_users")
        op.drop_column("sp_users", "invitation_token")
    if "token_expires_at" in cols:
        op.drop_column("sp_users", "token_expires_at")
