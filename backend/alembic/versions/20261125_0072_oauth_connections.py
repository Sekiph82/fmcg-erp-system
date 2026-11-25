"""M43.S00.T004: delegated OAuth connections and single-use OAuth states."""

from alembic import op

revision = "20261125_0072"
down_revision = "20261124_0071"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS oauth_connections (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            provider VARCHAR(20) NOT NULL,
            purpose VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'CONNECTED',
            account_email VARCHAR(255),
            scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
            access_token_enc TEXT,
            refresh_token_enc TEXT,
            expires_at TIMESTAMPTZ,
            sync_cursor JSONB,
            last_error VARCHAR(500),
            last_sync_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_oauth_conn_user_provider_purpose UNIQUE (user_id, provider, purpose)
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_oauth_connections_user_id ON oauth_connections (user_id)")
    op.execute("""
        CREATE TABLE IF NOT EXISTS oauth_states (
            state VARCHAR(64) PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            provider VARCHAR(20) NOT NULL,
            purpose VARCHAR(20) NOT NULL,
            code_verifier_enc TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL
        )""")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS oauth_states")
    op.execute("DROP TABLE IF EXISTS oauth_connections")
