"""M36.S05.T004 conversation intelligence findings and coaching review."""

from alembic import op

revision = "20261121_0064"
down_revision = "20261121_0063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_conversation_insights (
            id UUID PRIMARY KEY,
            source_type VARCHAR(8) NOT NULL CHECK (source_type IN ('call','chat')),
            source_id UUID NOT NULL,
            agent_id UUID REFERENCES users(id) ON DELETE SET NULL,
            findings JSON NOT NULL DEFAULT '[]',
            counts JSON NOT NULL DEFAULT '{}',
            engine VARCHAR(12) NOT NULL DEFAULT 'rules',
            status VARCHAR(16) NOT NULL DEFAULT 'PENDING_REVIEW' CHECK (status IN ('PENDING_REVIEW','REVIEWED','REJECTED')),
            coaching_note TEXT,
            analysed_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            analysed_at TIMESTAMPTZ,
            reviewed_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            reviewed_at TIMESTAMPTZ,
            CONSTRAINT uq_crm_conversation_insight_source UNIQUE (source_type, source_id)
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_crm_conversation_insights_agent ON crm_conversation_insights (agent_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS crm_conversation_insights")
