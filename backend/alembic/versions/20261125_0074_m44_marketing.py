"""M44 Advanced Marketing Hub: e-mail designs, deliverability, governance, analytics, audiences, ads, social, channels."""

from alembic import op

revision = "20261125_0074"
down_revision = "20261125_0073"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # T001: visual e-mail designs
    op.execute("""
        CREATE TABLE IF NOT EXISTS mkt_email_designs (
            id UUID PRIMARY KEY,
            family_id UUID NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            name VARCHAR(150) NOT NULL,
            preheader VARCHAR(200),
            document JSON NOT NULL,
            status VARCHAR(10) NOT NULL DEFAULT 'DRAFT',
            created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_email_design_family_version UNIQUE (family_id, version)
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_mkt_email_designs_family ON mkt_email_designs (family_id)")
    op.execute("ALTER TABLE crm_email_campaigns ADD COLUMN IF NOT EXISTS design_id UUID REFERENCES mkt_email_designs(id) ON DELETE RESTRICT")
    op.execute("ALTER TABLE crm_outbound_messages ADD COLUMN IF NOT EXISTS body_html TEXT")

    # T011: verified mail feedback events
    op.execute("""
        CREATE TABLE IF NOT EXISTS mail_feedback_events (
            id UUID PRIMARY KEY,
            provider VARCHAR(20) NOT NULL,
            event_id VARCHAR(200) NOT NULL,
            kind VARCHAR(15) NOT NULL,
            email VARCHAR(254),
            message_id VARCHAR(300),
            outbound_id UUID REFERENCES crm_outbound_messages(id) ON DELETE SET NULL,
            applied BOOLEAN NOT NULL DEFAULT false,
            received_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT uq_mail_feedback_event UNIQUE (provider, event_id)
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_mail_feedback_email ON mail_feedback_events (email)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS mail_feedback_events")
    op.execute("ALTER TABLE crm_outbound_messages DROP COLUMN IF EXISTS body_html")
    op.execute("ALTER TABLE crm_email_campaigns DROP COLUMN IF EXISTS design_id")
    op.execute("DROP TABLE IF EXISTS mkt_email_designs")
