"""M36 review: make sure the named unique constraints/indexes exist even where tables were created from the models."""

from alembic import op

revision = "20261121_0067"
down_revision = "20261121_0066"
branch_labels = None
depends_on = None

CONSTRAINTS = [
    ("crm_landing_variants", "uq_crm_landing_variant_key", "UNIQUE (page_id, key)"),
    ("crm_landing_events", "uq_crm_landing_event_once", "UNIQUE (page_id, visitor_hash, kind)"),
    ("crm_workflow_versions", "uq_crm_workflow_version_no", "UNIQUE (workflow_id, version_no)"),
    ("crm_workflow_runs", "uq_crm_workflow_run_event", "UNIQUE (version_id, event_key)"),
    ("crm_conversation_insights", "uq_crm_conversation_insight_source", "UNIQUE (source_type, source_id)"),
]


def upgrade() -> None:
    for table, name, ddl in CONSTRAINTS:
        op.execute(f"""
            DO $$ BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '{name}') THEN
                ALTER TABLE {table} ADD CONSTRAINT {name} {ddl};
              END IF;
            END $$;""")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_crm_workflow_one_published ON crm_workflow_versions (workflow_id) WHERE status = 'PUBLISHED'")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_crm_account_contacts_customer_email ON crm_account_contacts (customer_id, lower(email)) WHERE email IS NOT NULL")
    op.execute("ALTER TABLE crm_landing_events ADD COLUMN IF NOT EXISTS ip_hash VARCHAR(64)")


def downgrade() -> None:
    pass
