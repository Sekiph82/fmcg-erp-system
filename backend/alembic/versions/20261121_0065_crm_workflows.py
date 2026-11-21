"""M36.S03.T004 visual workflow designer: workflows, versioned graphs, runs."""

from alembic import op

revision = "20261121_0065"
down_revision = "20261121_0064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_workflows (
            id UUID PRIMARY KEY,
            name VARCHAR(150) NOT NULL UNIQUE,
            trigger_event VARCHAR(20),
            published_version_id UUID,
            enqueued_until TIMESTAMPTZ,
            created_by VARCHAR(100),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_workflow_versions (
            id UUID PRIMARY KEY,
            workflow_id UUID NOT NULL REFERENCES crm_workflows(id) ON DELETE CASCADE,
            version_no INTEGER NOT NULL,
            graph JSON NOT NULL,
            status VARCHAR(10) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','PUBLISHED','ARCHIVED')),
            created_by VARCHAR(100),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            published_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            published_at TIMESTAMPTZ,
            CONSTRAINT uq_crm_workflow_version_no UNIQUE (workflow_id, version_no)
        )""")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_crm_workflow_one_published ON crm_workflow_versions (workflow_id) WHERE status = 'PUBLISHED'")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_workflow_runs (
            id UUID PRIMARY KEY,
            version_id UUID NOT NULL REFERENCES crm_workflow_versions(id) ON DELETE CASCADE,
            crm_record_id UUID NOT NULL REFERENCES crm_records(id) ON DELETE CASCADE,
            event_key VARCHAR(120) NOT NULL,
            current_node VARCHAR(40),
            waiting_node VARCHAR(40),
            status VARCHAR(16) NOT NULL DEFAULT 'RUNNING',
            resume_at TIMESTAMPTZ,
            log JSON NOT NULL DEFAULT '[]',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            finished_at TIMESTAMPTZ,
            CONSTRAINT uq_crm_workflow_run_event UNIQUE (version_id, event_key)
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_crm_workflow_runs_due ON crm_workflow_runs (status, resume_at)")


def downgrade() -> None:
    for t in ("crm_workflow_runs", "crm_workflow_versions", "crm_workflows"):
        op.execute(f"DROP TABLE IF EXISTS {t}")
