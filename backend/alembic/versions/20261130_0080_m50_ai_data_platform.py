"""M50 AI and data platform: prospecting agent (ICP, research, enrichment, intent), grounded customer-service agent
and support QA, agent workflow gates/templates, atomic AI budgets and usage log, AI evaluation runs, common data sync
proposals/conflicts, SAML SSO, business-card OCR drafts and Gmail/Outlook add-in grants.

Tables are created from their ORM definitions (checkfirst), like 0075-0079. Downgrade archives evidence tables
(consent, approvals, budgets/usage, evaluations, sync journals, grants) instead of dropping them (audit F3 rule).
"""

from alembic import op

revision = "20261130_0080"
down_revision = "20261129_0079"
branch_labels = None
depends_on = None

TABLES = [
    "m50_provider_settings", "m50_icp_profiles", "m50_agent_runs", "m50_candidates", "m50_research_queries",
    "m50_research_docs", "m50_enrichment_proposals", "m50_intent_events", "m50_intent_alerts",          # T001-T004
    "sa_turns", "sa_actions", "kb_gap_proposals",                                                     # T005-T006
    "ai_agent_gates", "ai_agent_templates", "ai_budget_counters", "ai_budget_reservations", "ai_usage_log",
    "ai_eval_runs", "ai_eval_case_results",                                                          # T007/T008/T012
    "m50_sync_options", "m50_sync_proposals", "m50_sync_conflicts", "m50_saml_configs", "m50_saml_requests",
    "m50_saml_assertions", "m50_ocr_card_drafts", "m50_addin_grants",                                # T009-T011
]

EVIDENCE = ["m50_provider_settings", "m50_agent_runs", "m50_candidates", "m50_enrichment_proposals", "m50_intent_events",
            "sa_turns", "kb_gap_proposals", "ai_agent_gates", "ai_budget_counters", "ai_budget_reservations",
            "ai_usage_log", "ai_eval_runs", "ai_eval_case_results", "m50_sync_proposals", "m50_sync_conflicts",
            "m50_ocr_card_drafts", "m50_addin_grants", "sa_actions"]


def _tables():
    import app.models  # noqa: F401
    from app.db.base import Base
    return [Base.metadata.tables[n] for n in TABLES]


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("ALTER TABLE dw_jobs ALTER COLUMN file_format TYPE VARCHAR(10)")     # T010: 'parquet'
    for t in _tables():
        t.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    from app.db.downgrade_archive import archive_tables
    bind = op.get_bind()
    archive_tables(bind, [n for n in reversed(TABLES) if n in EVIDENCE], "0080")
    for t in reversed(_tables()):
        if t.name not in EVIDENCE:
            t.drop(bind=bind, checkfirst=True)
    op.execute("UPDATE dw_jobs SET file_format = 'csv' WHERE file_format = 'parquet'")   # 0079 cannot hold 'parquet'
    op.execute("ALTER TABLE dw_jobs ALTER COLUMN file_format TYPE VARCHAR(6)")
