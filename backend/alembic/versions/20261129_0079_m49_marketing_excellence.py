"""M49 CRM, advertising and social marketing excellence: recurring meetings, calendar webhooks, shared mailboxes,
contact center and transcription, social formats and listening, ad lifecycle edits, audience synchronisation.

Tables are created from their ORM definitions (checkfirst), like 0075-0078; column additions are explicit SQL.
Downgrade archives evidence tables (recordings, transcripts, consent/suppression, provider receipts) instead of dropping
them (audit F3 rule) and drops the rest.
"""

from alembic import op

revision = "20261129_0079"
down_revision = "20261128_0078"
branch_labels = None
depends_on = None

TABLES = [
    "meeting_series", "meeting_series_occurrences", "meeting_series_calendar_links",                  # T001
    "calendar_subscriptions", "calendar_webhook_receipts",                                           # T002
    "shared_mailboxes", "shared_mailbox_members",                                                    # T003
    "voice_queues", "voice_queue_entries", "voice_agent_presence", "voice_callbacks", "voice_transfers",
    "voice_call_dispositions", "voice_voicemails", "voice_provider_events",                           # T004
    "m49_transcript_jobs", "m49_transcript_edits",                                                   # T005
    "m49_ad_edits",                                                                                  # T006
    "m49_social_post_metrics", "m49_social_optouts", "m49_social_webhook_events", "m49_social_quota_use",
    "m49_audience_syncs", "m49_audience_sync_members", "m49_audience_suppressions",                  # T011
    "m49_studio_campaigns", "m49_studio_links", "m49_studio_budget_requests",                        # T012
]

COLUMNS = [
    ("social_channels", "options", "JSON"),                                                          # T007-T010
    ("social_posts", "format", "VARCHAR(24)"),
    ("social_posts", "format_options", "JSON"),
    ("social_posts", "flow_state", "JSON"),
    ("social_items", "reply_status", "VARCHAR(9)"),
    ("social_items", "reply_requested_by", "VARCHAR(100)"),
    ("social_items", "reply_approved_by", "VARCHAR(100)"),
    ("social_items", "reply_external_id", "VARCHAR(120)"),
    ("social_items", "reply_error", "VARCHAR(500)"),
    ("social_items", "provider_state", "VARCHAR(9)"),
    ("social_items", "retention_until", "TIMESTAMPTZ"),
]

EVIDENCE = ["voice_voicemails", "voice_provider_events", "m49_transcript_jobs", "m49_transcript_edits",
            "calendar_webhook_receipts", "m49_social_optouts", "m49_social_webhook_events", "m49_audience_suppressions",
            "m49_ad_edits", "m49_studio_budget_requests"]


def _tables():
    import app.models  # noqa: F401
    from app.db.base import Base
    return [Base.metadata.tables[n] for n in TABLES]


def upgrade() -> None:
    bind = op.get_bind()
    for table, col, ddl in COLUMNS:
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {ddl}")
    for t in _tables():
        t.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    from app.db.downgrade_archive import archive_tables
    bind = op.get_bind()
    archive_tables(bind, [n for n in reversed(TABLES) if n in EVIDENCE], "0079")
    for t in reversed(_tables()):
        if t.name not in EVIDENCE:
            t.drop(bind=bind, checkfirst=True)
    for table, col, _ in reversed(COLUMNS):
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {col}")
