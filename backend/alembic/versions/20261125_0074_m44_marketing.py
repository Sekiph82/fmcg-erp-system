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

    # T012: A/B, send-time optimisation, approval
    for col, ddl in (("ab_split_pct", "INTEGER NOT NULL DEFAULT 0 CHECK (ab_split_pct BETWEEN 0 AND 50)"),
                     ("variant_b_subject", "VARCHAR(300)"), ("variant_b_body", "TEXT"),
                     ("variant_b_design_id", "UUID REFERENCES mkt_email_designs(id) ON DELETE RESTRICT"),
                     ("send_time_optimize", "BOOLEAN NOT NULL DEFAULT false"),
                     ("approval_status", "VARCHAR(10) NOT NULL DEFAULT 'NONE'"), ("approval_requested_by", "VARCHAR(100)"),
                     ("approved_by", "VARCHAR(100)"), ("approved_at", "TIMESTAMPTZ")):
        op.execute(f"ALTER TABLE crm_email_campaigns ADD COLUMN IF NOT EXISTS {col} {ddl}")
    op.execute("ALTER TABLE crm_outbound_messages ADD COLUMN IF NOT EXISTS ab_variant VARCHAR(1)")

    # T009: first-party web analytics
    op.execute("""
        CREATE TABLE IF NOT EXISTS web_events (
            id UUID PRIMARY KEY, visitor_hash VARCHAR(64) NOT NULL, session_id VARCHAR(64) NOT NULL,
            event_id VARCHAR(64) NOT NULL, kind VARCHAR(10) NOT NULL, name VARCHAR(100), path VARCHAR(300) NOT NULL,
            referrer_host VARCHAR(200), utm_source VARCHAR(100), utm_medium VARCHAR(100), utm_campaign VARCHAR(100),
            occurred_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT uq_web_event_visitor_event UNIQUE (visitor_hash, event_id))""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_web_events_time ON web_events (occurred_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_web_events_visitor ON web_events (visitor_hash, occurred_at)")
    op.execute("""CREATE TABLE IF NOT EXISTS web_identities (visitor_hash VARCHAR(64) PRIMARY KEY,
                  email VARCHAR(254) NOT NULL, linked_at TIMESTAMPTZ NOT NULL)""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_web_identities_email ON web_identities (email)")
    op.execute("""CREATE TABLE IF NOT EXISTS web_consents (id UUID PRIMARY KEY, visitor_hash VARCHAR(64) NOT NULL,
                  analytics BOOLEAN NOT NULL, marketing BOOLEAN NOT NULL, decided_at TIMESTAMPTZ NOT NULL)""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_web_consents_visitor_hash ON web_consents (visitor_hash)")

    # T010: dynamic audiences
    op.execute("""
        CREATE TABLE IF NOT EXISTS mkt_audiences (
            id UUID PRIMARY KEY, name VARCHAR(150) NOT NULL UNIQUE, rules JSON NOT NULL,
            require_consent BOOLEAN NOT NULL DEFAULT true, member_count INTEGER NOT NULL DEFAULT 0,
            blocked_count INTEGER NOT NULL DEFAULT 0, computed_at TIMESTAMPTZ,
            created_by_id UUID REFERENCES users(id) ON DELETE SET NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS mkt_audience_members (
            audience_id UUID NOT NULL REFERENCES mkt_audiences(id) ON DELETE CASCADE,
            customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
            email VARCHAR(254) NOT NULL, added_at TIMESTAMPTZ NOT NULL, PRIMARY KEY (audience_id, customer_id))""")


def downgrade() -> None:
    for t in ("mkt_audience_members", "mkt_audiences"):
        op.execute(f"DROP TABLE IF EXISTS {t}")
    for t in ("web_consents", "web_identities", "web_events"):
        op.execute(f"DROP TABLE IF EXISTS {t}")
    op.execute("ALTER TABLE crm_outbound_messages DROP COLUMN IF EXISTS ab_variant")
    for col in ("approved_at", "approved_by", "approval_requested_by", "approval_status", "send_time_optimize",
                "variant_b_design_id", "variant_b_body", "variant_b_subject", "ab_split_pct"):
        op.execute(f"ALTER TABLE crm_email_campaigns DROP COLUMN IF EXISTS {col}")
    op.execute("DROP TABLE IF EXISTS mail_feedback_events")
    op.execute("ALTER TABLE crm_outbound_messages DROP COLUMN IF EXISTS body_html")
    op.execute("ALTER TABLE crm_email_campaigns DROP COLUMN IF EXISTS design_id")
    op.execute("DROP TABLE IF EXISTS mkt_email_designs")
