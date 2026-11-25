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


def downgrade() -> None:
    op.execute("ALTER TABLE crm_outbound_messages DROP COLUMN IF EXISTS body_html")
    op.execute("ALTER TABLE crm_email_campaigns DROP COLUMN IF EXISTS design_id")
    op.execute("DROP TABLE IF EXISTS mkt_email_designs")
