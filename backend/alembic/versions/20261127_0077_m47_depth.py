"""M47 depth tasks (T007–T011) and audit fixes.

Tables are created from their ORM definitions (checkfirst), like 0075/0076; column additions are explicit SQL.
Downgrade drops them: video messages, recaps, datasets, workflow hooks and event definitions are lost.
"""

from alembic import op

revision = "20261127_0077"
down_revision = "20261127_0076"
branch_labels = None
depends_on = None

# Parents first (downgrade drops in reverse).
TABLES = [
    "rb_datasets",                                                                     # T011
    "crm_workflow_hooks", "web_event_definitions", "web_event_properties",             # T008
    "crm_task_calendar_links", "sales_video_messages", "sales_video_views",            # T009
    "meeting_recaps", "sales_ai_usage",
    "field_permission_rules", "crm_contact_properties", "crm_lead_form_settings", "crm_slack_routes",       # T010
    "crm_slack_user_links", "ads_audience_uploads", "ads_conversion_uploads",
    "helpdesk_pipelines", "helpdesk_pipeline_stages", "helpdesk_ticket_stages",
    "whatsapp_consents",                                                                # T003 WhatsApp opt-in/STOP
]

COLUMNS = [
    ("cms_media", "page_id", "UUID REFERENCES cms_pages(id) ON DELETE SET NULL"),       # T007 narration audio ↔ page
    ("cms_media", "poster_path", "VARCHAR(40)"),                                        # T007 poster frame
]

INDEXES = [
    ("ix_cms_media_page_id", "cms_media", "page_id"),
]


def _tables():
    import app.models  # noqa: F401
    from app.db.base import Base
    return [Base.metadata.tables[n] for n in TABLES]


def upgrade() -> None:
    bind = op.get_bind()
    for table, col, ddl in COLUMNS:
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {ddl}")
    for name, table, col in INDEXES:
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({col})")
    for t in _tables():
        t.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for t in reversed(_tables()):
        t.drop(bind=bind, checkfirst=True)
    for name, _, _ in INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {name}")
    for table, col, _ in reversed(COLUMNS):
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {col}")
