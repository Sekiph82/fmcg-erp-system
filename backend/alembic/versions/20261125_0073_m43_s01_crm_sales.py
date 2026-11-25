"""M43.S01 Advanced CRM & Sales: OAuth mailboxes and calendars, booking pages, tracking, quotas, voice,
playbooks, pipelines, deal scoring, workspace, routing, contacts/associations, teams and views."""

from alembic import op

revision = "20261125_0073"
down_revision = "20261125_0072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # T001/T002: a mailbox may be connected through delegated OAuth (Gmail API / Microsoft Graph)
    op.execute("""ALTER TABLE email_accounts ADD COLUMN IF NOT EXISTS oauth_connection_id UUID
                  REFERENCES oauth_connections(id) ON DELETE SET NULL""")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_email_accounts_oauth ON email_accounts (oauth_connection_id) "
               "WHERE oauth_connection_id IS NOT NULL")

    # T003/T004: two-way calendar sync
    op.execute("""
        CREATE TABLE IF NOT EXISTS calendar_event_links (
            id UUID PRIMARY KEY,
            meeting_id UUID NOT NULL REFERENCES meeting_records(id) ON DELETE CASCADE,
            connection_id UUID NOT NULL REFERENCES oauth_connections(id) ON DELETE CASCADE,
            external_event_id VARCHAR(1024),
            etag VARCHAR(255),
            pushed_sequence INTEGER,
            conflict VARCHAR(500),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_cal_link_meeting_conn UNIQUE (meeting_id, connection_id),
            CONSTRAINT uq_cal_link_conn_event UNIQUE (connection_id, external_event_id)
        )""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS calendar_busy_blocks (
            id UUID PRIMARY KEY,
            connection_id UUID NOT NULL REFERENCES oauth_connections(id) ON DELETE CASCADE,
            external_event_id VARCHAR(1024) NOT NULL,
            starts_at TIMESTAMP NOT NULL,
            ends_at TIMESTAMP NOT NULL,
            CONSTRAINT uq_busy_conn_event UNIQUE (connection_id, external_event_id)
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_busy_conn_time ON calendar_busy_blocks (connection_id, starts_at, ends_at)")

    # T005: public self-booking pages
    op.execute("""
        CREATE TABLE IF NOT EXISTS booking_pages (
            id UUID PRIMARY KEY,
            slug VARCHAR(80) NOT NULL UNIQUE,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            duration_minutes INTEGER NOT NULL DEFAULT 30 CHECK (duration_minutes BETWEEN 5 AND 480),
            buffer_before INTEGER NOT NULL DEFAULT 0 CHECK (buffer_before BETWEEN 0 AND 240),
            buffer_after INTEGER NOT NULL DEFAULT 10 CHECK (buffer_after BETWEEN 0 AND 240),
            min_notice_hours INTEGER NOT NULL DEFAULT 4 CHECK (min_notice_hours BETWEEN 0 AND 720),
            max_days_ahead INTEGER NOT NULL DEFAULT 30 CHECK (max_days_ahead BETWEEN 1 AND 365),
            time_zone VARCHAR(64) NOT NULL DEFAULT 'Africa/Nairobi',
            open_time VARCHAR(5) NOT NULL DEFAULT '08:00',
            close_time VARCHAR(5) NOT NULL DEFAULT '17:00',
            weekdays JSON NOT NULL DEFAULT '[0,1,2,3,4]',
            host_ids JSON NOT NULL DEFAULT '[]',
            routing VARCHAR(20) NOT NULL DEFAULT 'round_robin',
            platform VARCHAR(30) NOT NULL DEFAULT 'jitsi',
            consent_text TEXT,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS booking_page_bookings (
            id UUID PRIMARY KEY,
            page_id UUID NOT NULL REFERENCES booking_pages(id) ON DELETE CASCADE,
            meeting_id UUID NOT NULL REFERENCES meeting_records(id) ON DELETE CASCADE,
            host_id UUID REFERENCES users(id) ON DELETE SET NULL,
            visitor_name VARCHAR(200) NOT NULL,
            visitor_email VARCHAR(255) NOT NULL,
            consent_text TEXT,
            manage_token_hash VARCHAR(64) NOT NULL UNIQUE,
            ip_hash VARCHAR(64),
            reminder_sent_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bookings_page_created ON booking_page_bookings (page_id, created_at)")

    # T006: opt-in e-mail engagement tracking
    op.execute("ALTER TABLE crm_contact_consents ADD COLUMN IF NOT EXISTS tracking_opt_out BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE crm_outbound_messages ADD COLUMN IF NOT EXISTS track_engagement BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE crm_outbound_messages ADD COLUMN IF NOT EXISTS tracked_links JSON")
    op.execute("ALTER TABLE crm_sequences ADD COLUMN IF NOT EXISTS track_engagement BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE crm_email_campaigns ADD COLUMN IF NOT EXISTS track_engagement BOOLEAN NOT NULL DEFAULT false")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_email_events (
            id UUID PRIMARY KEY,
            message_id UUID NOT NULL REFERENCES crm_outbound_messages(id) ON DELETE CASCADE,
            kind VARCHAR(5) NOT NULL CHECK (kind IN ('OPEN', 'CLICK')),
            link_index INTEGER NOT NULL DEFAULT 0,
            url VARCHAR(2000),
            occurred_at TIMESTAMPTZ NOT NULL,
            is_machine BOOLEAN NOT NULL DEFAULT false,
            ua_class VARCHAR(10),
            ip_hash VARCHAR(64)
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_crm_email_events_message ON crm_email_events (message_id, kind, occurred_at)")

    # T007: quotas, forecast category, snapshots
    op.execute("ALTER TABLE crm_records ADD COLUMN IF NOT EXISTS forecast_category VARCHAR(10) "
               "CHECK (forecast_category IN ('PIPELINE', 'BEST_CASE', 'COMMIT', 'OMITTED'))")
    op.execute("""
        CREATE TABLE IF NOT EXISTS sales_quotas (
            id UUID PRIMARY KEY,
            scope_type VARCHAR(10) NOT NULL CHECK (scope_type IN ('REP', 'TEAM', 'TERRITORY', 'COMPANY')),
            scope_ref VARCHAR(100) NOT NULL,
            scope_label VARCHAR(200),
            period_type VARCHAR(10) NOT NULL,
            period_start DATE NOT NULL,
            period_end DATE NOT NULL CHECK (period_end >= period_start),
            currency VARCHAR(10) NOT NULL,
            target_amount NUMERIC(18, 2) NOT NULL CHECK (target_amount > 0),
            company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
            notes TEXT,
            created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_sales_quota_scope_period_currency UNIQUE (scope_type, scope_ref, period_start, period_end, currency)
        )""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS sales_quota_snapshots (
            id UUID PRIMARY KEY,
            quota_id UUID NOT NULL REFERENCES sales_quotas(id) ON DELETE CASCADE,
            taken_at TIMESTAMPTZ NOT NULL,
            actual_amount NUMERIC(18, 2) NOT NULL,
            commit_amount NUMERIC(18, 2) NOT NULL,
            best_case_amount NUMERIC(18, 2) NOT NULL,
            pipeline_amount NUMERIC(18, 2) NOT NULL,
            projected_amount NUMERIC(18, 2) NOT NULL,
            assumptions JSON NOT NULL
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_quota_snapshots_quota ON sales_quota_snapshots (quota_id, taken_at)")

    # T008/T009: provider voice, IVR, power dialer, transcription
    op.execute("""
        CREATE TABLE IF NOT EXISTS voice_agent_profiles (
            user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            phone_number VARCHAR(50) NOT NULL,
            available BOOLEAN NOT NULL DEFAULT true
        )""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS voice_ivr_menus (
            id UUID PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            phone_number VARCHAR(50) NOT NULL UNIQUE,
            greeting_text TEXT NOT NULL,
            options JSONB NOT NULL DEFAULT '[]'::jsonb,
            record_calls BOOLEAN NOT NULL DEFAULT false,
            consent_text TEXT,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_ivr_record_consent CHECK (NOT record_calls OR consent_text IS NOT NULL)
        )""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS voice_dialer_sessions (
            id UUID PRIMARY KEY,
            agent_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(150) NOT NULL,
            status VARCHAR(10) NOT NULL DEFAULT 'ACTIVE',
            items JSONB NOT NULL DEFAULT '[]'::jsonb,
            current_index INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_voice_dialer_agent ON voice_dialer_sessions (agent_id)")
    for col, ddl in (("provider", "VARCHAR(30)"), ("provider_session_id", "VARCHAR(100)"), ("status", "VARCHAR(15)"),
                     ("ivr_menu_id", "UUID REFERENCES voice_ivr_menus(id) ON DELETE SET NULL"), ("ivr_step", "VARCHAR(20)"),
                     ("dialer_session_id", "UUID REFERENCES voice_dialer_sessions(id) ON DELETE SET NULL"),
                     ("cost_amount", "VARCHAR(20)"), ("cost_currency", "VARCHAR(10)"),
                     ("transcript_segments", "JSONB"), ("transcript_language", "VARCHAR(10)"),
                     ("transcription_status", "VARCHAR(15)"), ("transcription_error", "VARCHAR(300)"),
                     ("transcription_attempts", "INTEGER NOT NULL DEFAULT 0")):
        op.execute(f"ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS {col} {ddl}")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_call_logs_provider_session ON call_logs (provider_session_id) "
               "WHERE provider_session_id IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_call_logs_transcription ON call_logs (transcription_status) "
               "WHERE transcription_status = 'PENDING'")

    # T010: playbooks, runs and deal plans
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_playbooks (
            id UUID PRIMARY KEY,
            family_id UUID NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            name VARCHAR(150) NOT NULL,
            purpose VARCHAR(15) NOT NULL CHECK (purpose IN ('CALL', 'VISIT', 'QUALIFICATION', 'STAGE')),
            stage_id UUID REFERENCES crm_pipeline_stages(id) ON DELETE SET NULL,
            guidance TEXT,
            questions JSON NOT NULL DEFAULT '[]',
            blocks_stage_exit BOOLEAN NOT NULL DEFAULT false,
            status VARCHAR(16) NOT NULL DEFAULT 'DRAFT'
                CHECK (status IN ('DRAFT', 'PENDING_APPROVAL', 'PUBLISHED', 'RETIRED')),
            created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            approved_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            approved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_playbook_family_version UNIQUE (family_id, version)
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_crm_playbooks_family ON crm_playbooks (family_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_playbook_one_published ON crm_playbooks (family_id) "
               "WHERE status = 'PUBLISHED'")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_playbook_runs (
            id UUID PRIMARY KEY,
            playbook_id UUID NOT NULL REFERENCES crm_playbooks(id) ON DELETE RESTRICT,
            crm_record_id UUID NOT NULL REFERENCES crm_records(id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            answers JSON NOT NULL DEFAULT '{}',
            completed BOOLEAN NOT NULL DEFAULT false,
            completed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_playbook_runs_record ON crm_playbook_runs (crm_record_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_playbook_runs_playbook ON crm_playbook_runs (playbook_id)")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_deal_plans (
            id UUID PRIMARY KEY,
            crm_record_id UUID NOT NULL UNIQUE REFERENCES crm_records(id) ON DELETE CASCADE,
            title VARCHAR(200) NOT NULL,
            steps JSON NOT NULL DEFAULT '[]',
            shared BOOLEAN NOT NULL DEFAULT false,
            share_token_hash VARCHAR(64) UNIQUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS crm_deal_plans")
    op.execute("DROP TABLE IF EXISTS crm_playbook_runs")
    op.execute("DROP TABLE IF EXISTS crm_playbooks")
    op.execute("DROP INDEX IF EXISTS ix_call_logs_transcription")
    op.execute("DROP INDEX IF EXISTS uq_call_logs_provider_session")
    for col in ("transcription_attempts", "transcription_error", "transcription_status", "transcript_language",
                "transcript_segments", "cost_currency", "cost_amount", "dialer_session_id", "ivr_step", "ivr_menu_id",
                "status", "provider_session_id", "provider"):
        op.execute(f"ALTER TABLE call_logs DROP COLUMN IF EXISTS {col}")
    op.execute("DROP TABLE IF EXISTS voice_dialer_sessions")
    op.execute("DROP TABLE IF EXISTS voice_ivr_menus")
    op.execute("DROP TABLE IF EXISTS voice_agent_profiles")
    op.execute("DROP TABLE IF EXISTS sales_quota_snapshots")
    op.execute("DROP TABLE IF EXISTS sales_quotas")
    op.execute("ALTER TABLE crm_records DROP COLUMN IF EXISTS forecast_category")
    op.execute("DROP TABLE IF EXISTS crm_email_events")
    for t in ("crm_email_campaigns", "crm_sequences", "crm_outbound_messages"):
        op.execute(f"ALTER TABLE {t} DROP COLUMN IF EXISTS track_engagement")
    op.execute("ALTER TABLE crm_outbound_messages DROP COLUMN IF EXISTS tracked_links")
    op.execute("ALTER TABLE crm_contact_consents DROP COLUMN IF EXISTS tracking_opt_out")
    op.execute("DROP TABLE IF EXISTS booking_page_bookings")
    op.execute("DROP TABLE IF EXISTS booking_pages")
    op.execute("DROP TABLE IF EXISTS calendar_busy_blocks")
    op.execute("DROP TABLE IF EXISTS calendar_event_links")
    op.execute("DROP INDEX IF EXISTS uq_email_accounts_oauth")
    op.execute("ALTER TABLE email_accounts DROP COLUMN IF EXISTS oauth_connection_id")
