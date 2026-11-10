"""Create tables of model modules that were never registered on Base.metadata.

Twenty-one model modules (consumer complaints, IoT, NPD, loyalty, workflow, ...)
were not imported by ``app.models``, so neither the squashed baseline nor any
migration created their tables and their endpoints failed on a real database.
They are now registered; this revision creates any of those tables that are
missing (checkfirst), so existing databases catch up. M35 quality cost entries
reference ``consumer_complaints``, hence this runs before 20261110_0028.
"""

from alembic import op

revision = "20261110_0027b"
down_revision = "20261110_0027"
branch_labels = None
depends_on = None

TABLES = (
    "approval_requests", "approval_rules", "approval_steps", "asset_approval_stages", "brand_assets",
    "call_logs", "call_scripts", "cert_audit_entries", "channel_members", "channel_messages", "chat_channels",
    "consumer_complaints", "container_issuances", "container_returns", "container_types",
    "copacking_contracts", "copacking_runs", "customer_loyalty_accounts", "customer_tools",
    "dp_competitor_prices", "dp_price_recommendations", "email_accounts", "email_messages",
    "email_templates", "email_threads", "employee_surveys", "iot_alert_thresholds", "iot_alerts",
    "iot_channels", "iot_devices", "iot_ingest_messages", "iot_machine_states", "iot_sensor_data",
    "kb_article_revisions", "kb_articles", "kb_categories", "loyalty_tiers", "loyalty_transactions",
    "market_observations", "market_share_estimates", "meeting_records", "mobile_app_sessions",
    "mobile_push_tokens", "npd_pilot_batches", "npd_projects", "npd_stage_gates", "nps_responses",
    "nps_surveys", "receipt_ocr_records", "regulatory_certificates", "survey_questions",
    "survey_responses", "whatsapp_configs", "whatsapp_messages", "whatsapp_templates",
)


def _tables():
    from app.db.base import Base
    import app.models  # noqa: F401

    return [Base.metadata.tables[name] for name in TABLES]


def upgrade() -> None:
    from app.db.base import Base

    Base.metadata.create_all(bind=op.get_bind(), tables=_tables(), checkfirst=True)


def downgrade() -> None:
    # Tables that existed before this revision (iot/kb/npd reconciliations) are owned by
    # earlier revisions; this downgrade leaves all of them in place rather than drop data.
    pass
