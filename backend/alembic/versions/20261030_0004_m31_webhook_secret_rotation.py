"""Add versioned webhook secret rotation with a bounded previous-key window."""

from alembic import op
import sqlalchemy as sa


revision = "20261030_0004"
down_revision = "20261030_0003"
branch_labels = None
depends_on = None


_TABLES = ("webhook_subscriptions", "webhook_inbound_endpoints")


def upgrade() -> None:
    bind = op.get_bind()
    for table in _TABLES:
        columns = {column["name"] for column in sa.inspect(bind).get_columns(table)}
        if "previous_secret_key" not in columns:
            op.add_column(table, sa.Column("previous_secret_key", sa.String(length=512), nullable=True))
        if "previous_secret_expires_at" not in columns:
            op.add_column(
                table,
                sa.Column("previous_secret_expires_at", sa.DateTime(timezone=True), nullable=True),
            )
        if "secret_version" not in columns:
            op.add_column(
                table,
                sa.Column("secret_version", sa.Integer(), nullable=False, server_default="1"),
            )
            op.alter_column(table, "secret_version", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(_TABLES):
        columns = {column["name"] for column in sa.inspect(bind).get_columns(table)}
        for name in ("secret_version", "previous_secret_expires_at", "previous_secret_key"):
            if name in columns:
                op.drop_column(table, name)
