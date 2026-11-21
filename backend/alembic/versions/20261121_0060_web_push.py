"""M37.S03.T001 Web Push subscriptions for the installed PWA."""

from alembic import op

revision = "20261121_0060"
down_revision = "20261121_0059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS web_push_subscriptions (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            endpoint VARCHAR(1000) NOT NULL UNIQUE,
            p256dh VARCHAR(200) NOT NULL,
            auth VARCHAR(100) NOT NULL,
            user_agent VARCHAR(300),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_sent_at TIMESTAMPTZ
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_web_push_subscriptions_user_id ON web_push_subscriptions (user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS web_push_subscriptions")
