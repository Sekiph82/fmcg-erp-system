"""M36.S05.T002 landing pages, variants and once-per-visitor view/conversion events."""

from alembic import op

revision = "20261121_0063"
down_revision = "20261121_0062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_landing_pages (
            id UUID PRIMARY KEY,
            slug VARCHAR(80) NOT NULL UNIQUE,
            name VARCHAR(150) NOT NULL,
            status VARCHAR(8) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','LIVE','PAUSED')),
            lead_form_id UUID NOT NULL REFERENCES crm_lead_forms(id) ON DELETE RESTRICT,
            min_sample INTEGER NOT NULL DEFAULT 100 CHECK (min_sample BETWEEN 10 AND 1000000),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_landing_variants (
            id UUID PRIMARY KEY,
            page_id UUID NOT NULL REFERENCES crm_landing_pages(id) ON DELETE CASCADE,
            key VARCHAR(4) NOT NULL,
            headline VARCHAR(200) NOT NULL,
            body TEXT,
            cta_label VARCHAR(60) NOT NULL DEFAULT 'Send',
            weight INTEGER NOT NULL DEFAULT 50 CHECK (weight BETWEEN 0 AND 100),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            CONSTRAINT uq_crm_landing_variant_key UNIQUE (page_id, key)
        )""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_landing_events (
            id UUID PRIMARY KEY,
            page_id UUID NOT NULL REFERENCES crm_landing_pages(id) ON DELETE CASCADE,
            variant_id UUID NOT NULL REFERENCES crm_landing_variants(id) ON DELETE CASCADE,
            visitor_hash VARCHAR(64) NOT NULL,
            kind VARCHAR(8) NOT NULL CHECK (kind IN ('VIEW','CONVERT')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_crm_landing_event_once UNIQUE (page_id, visitor_hash, kind)
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_crm_landing_events_variant ON crm_landing_events (variant_id)")


def downgrade() -> None:
    for t in ("crm_landing_events", "crm_landing_variants", "crm_landing_pages"):
        op.execute(f"DROP TABLE IF EXISTS {t}")
