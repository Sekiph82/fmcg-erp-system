"""Create storage for Developer Portal API keys and usage logs."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261021_0010"
down_revision = "20261020_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dev_api_keys",
        sa.Column("key_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(100), nullable=False),
        sa.Column("key_name", sa.String(200), nullable=False),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("key_hash", sa.String(256), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=True),
        sa.Column("rate_limit_per_min", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint("key_hash", name="uq_dev_api_keys_key_hash"),
    )
    op.create_index("ix_dev_api_keys_user_id", "dev_api_keys", ["user_id"])

    op.create_table(
        "dev_api_key_usage_logs",
        sa.Column("log_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dev_api_keys.key_id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint", sa.String(500), nullable=True),
        sa.Column("method", sa.String(10), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_ms", sa.Integer(), nullable=True),
        sa.Column("ip_address", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_dev_api_key_usage_logs_key_id", "dev_api_key_usage_logs", ["key_id"])


def downgrade() -> None:
    op.drop_index("ix_dev_api_key_usage_logs_key_id", table_name="dev_api_key_usage_logs")
    op.drop_table("dev_api_key_usage_logs")
    op.drop_index("ix_dev_api_keys_user_id", table_name="dev_api_keys")
    op.drop_table("dev_api_keys")
