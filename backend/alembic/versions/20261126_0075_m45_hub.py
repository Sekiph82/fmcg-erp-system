"""M45 AI Agent & Customer Data Hub.

New tables are created from their ORM definitions (checkfirst), the same way the squashed baseline creates tables, so
the migration and the models cannot drift apart. Column additions to existing tables are explicit SQL.
Downgrade drops the M45 tables and columns: data in them is lost (see docs/DEPLOYMENT.md).
"""

from alembic import op

revision = "20261126_0075"
down_revision = "20261125_0074"
branch_labels = None
depends_on = None

# Order matters for foreign keys: parents first (downgrade drops in reverse).
TABLES = [
    "ci_settings", "ci_models", "ci_alerts", "ci_health_snapshots",
    "personal_access_tokens", "ai_action_requests", "ai_agents", "ai_agent_versions", "ai_agent_jobs",
    "cd_sources", "cd_prospects", "cd_facts", "cd_verified_fields", "cd_prospect_runs", "cd_merges", "cd_dup_dismissals", "cd_sensitive_fields",
    "co_types", "co_records", "co_associations",
    "auth_impersonations", "nc_notification_policies", "auth_sso_configs", "auth_sso_states",
    "pay_links", "pay_link_attempts", "doc_share_links", "doc_share_events",
]

COLUMNS = [
    ("crm_contacts", "language", "VARCHAR(8)"),
    ("crm_chat_sessions", "portal_account_id", "UUID REFERENCES portal_accounts(id) ON DELETE SET NULL"),
]


def _tables():
    import app.models  # noqa: F401  (registers every model on Base.metadata)
    from app.db.base import Base
    return [Base.metadata.tables[n] for n in TABLES]


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("ALTER TYPE documentcategory ADD VALUE IF NOT EXISTS 'SALES_DOCUMENT'")   # T013 (kept on downgrade: PG cannot drop enum values)
    for table, col, ddl in COLUMNS:
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {ddl}")
    for t in _tables():
        t.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for t in reversed(_tables()):
        t.drop(bind=bind, checkfirst=True)
    for table, col, _ in reversed(COLUMNS):
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {col}")
