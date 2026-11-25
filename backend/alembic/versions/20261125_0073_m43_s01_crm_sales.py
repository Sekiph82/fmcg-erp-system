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

    # T011: multiple pipelines; every existing stage and record moves into one default pipeline (no data loss)
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_pipelines (
            id UUID PRIMARY KEY,
            name VARCHAR(120) NOT NULL UNIQUE,
            record_type VARCHAR(20),
            company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
            is_default BOOLEAN NOT NULL DEFAULT false,
            active_flag BOOLEAN NOT NULL DEFAULT true,
            sequence_no INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_crm_pipelines_one_default ON crm_pipelines (is_default) WHERE is_default")
    op.execute("""INSERT INTO crm_pipelines (id, name, is_default, active_flag, sequence_no)
                  SELECT gen_random_uuid(), 'Sales pipeline', true, true, 0
                  WHERE NOT EXISTS (SELECT 1 FROM crm_pipelines WHERE is_default)""")
    op.execute("ALTER TABLE crm_pipeline_stages ADD COLUMN IF NOT EXISTS pipeline_id UUID REFERENCES crm_pipelines(id) ON DELETE RESTRICT")
    op.execute("UPDATE crm_pipeline_stages SET pipeline_id = (SELECT id FROM crm_pipelines WHERE is_default) WHERE pipeline_id IS NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_crm_pipeline_stages_pipeline ON crm_pipeline_stages (pipeline_id)")
    op.execute("ALTER TABLE crm_records ADD COLUMN IF NOT EXISTS pipeline_id UUID REFERENCES crm_pipelines(id) ON DELETE SET NULL")
    op.execute("""UPDATE crm_records r SET pipeline_id = s.pipeline_id FROM crm_pipeline_stages s
                  WHERE r.stage_id = s.id AND r.pipeline_id IS NULL""")
    op.execute("UPDATE crm_records SET pipeline_id = (SELECT id FROM crm_pipelines WHERE is_default) WHERE pipeline_id IS NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_crm_records_pipeline ON crm_records (pipeline_id)")

    # T015: standalone contacts, associations, lifecycle; backfilled from CRM records and account contacts
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_contacts (
            id UUID PRIMARY KEY,
            full_name VARCHAR(200) NOT NULL,
            email VARCHAR(254),
            phone VARCHAR(50),
            job_title VARCHAR(150),
            lifecycle_stage VARCHAR(12) CHECK (lifecycle_stage IN
                ('SUBSCRIBER', 'LEAD', 'MQL', 'SQL', 'OPPORTUNITY', 'CUSTOMER', 'EVANGELIST', 'OTHER')),
            lifecycle_changed_at TIMESTAMPTZ,
            owner_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
            source VARCHAR(60),
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_crm_contacts_email ON crm_contacts (lower(email)) WHERE email IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_crm_contacts_company ON crm_contacts (company_id)")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_contact_associations (
            id UUID PRIMARY KEY,
            contact_id UUID NOT NULL REFERENCES crm_contacts(id) ON DELETE CASCADE,
            object_type VARCHAR(20) NOT NULL CHECK (object_type IN ('customer', 'crm_record', 'ticket', 'quotation', 'sales_order')),
            object_id UUID NOT NULL,
            label VARCHAR(20) NOT NULL DEFAULT 'primary',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_contact_assoc UNIQUE (contact_id, object_type, object_id, label)
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_contact_assoc_object ON crm_contact_associations (object_type, object_id)")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_lifecycle_history (
            id UUID PRIMARY KEY,
            contact_id UUID NOT NULL REFERENCES crm_contacts(id) ON DELETE CASCADE,
            from_stage VARCHAR(12),
            to_stage VARCHAR(12) NOT NULL,
            source VARCHAR(60) NOT NULL,
            reason VARCHAR(300),
            changed_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            changed_at TIMESTAMPTZ NOT NULL
        )""")
    op.execute("ALTER TABLE crm_account_contacts ADD COLUMN IF NOT EXISTS contact_id UUID REFERENCES crm_contacts(id) ON DELETE SET NULL")
    # backfill 1: one contact per distinct e-mail across CRM records and account contacts (newest name wins)
    op.execute("""
        INSERT INTO crm_contacts (id, full_name, email, phone, job_title, company_id, source, created_at, updated_at)
        SELECT gen_random_uuid(), name, email, phone, title, company_id, src, now(), now() FROM (
            SELECT DISTINCT ON (lower(email)) name, lower(email) AS email, phone, title, company_id, src FROM (
                SELECT COALESCE(NULLIF(trim(contact_person_name), ''), contact_email) AS name, contact_email AS email,
                       contact_phone AS phone, NULL::varchar AS title, company_id, 'migration:crm_record' AS src, created_at AS ts
                  FROM crm_records WHERE NULLIF(trim(contact_email), '') IS NOT NULL
                UNION ALL
                SELECT full_name, email, phone, title, NULL::uuid, 'migration:account_contact', now()
                  FROM crm_account_contacts WHERE NULLIF(trim(email), '') IS NOT NULL
            ) src ORDER BY lower(email), ts DESC
        ) d
        ON CONFLICT DO NOTHING""")
    # backfill 2: records with a contact name but no e-mail get their own contact (cannot be safely merged)
    op.execute("""
        INSERT INTO crm_contacts (id, full_name, phone, company_id, source, created_at, updated_at)
        SELECT r.id, trim(r.contact_person_name), r.contact_phone, r.company_id, 'migration:crm_record:no_email', now(), now()
          FROM crm_records r
         WHERE NULLIF(trim(r.contact_email), '') IS NULL AND NULLIF(trim(r.contact_person_name), '') IS NOT NULL
        ON CONFLICT DO NOTHING""")
    op.execute("""
        INSERT INTO crm_contact_associations (id, contact_id, object_type, object_id, label, created_at)
        SELECT gen_random_uuid(), COALESCE(c.id, r.id), 'crm_record', r.id, 'primary', now()
          FROM crm_records r LEFT JOIN crm_contacts c ON lower(c.email) = lower(NULLIF(trim(r.contact_email), ''))
         WHERE COALESCE(c.id, (SELECT id FROM crm_contacts WHERE id = r.id)) IS NOT NULL
        ON CONFLICT DO NOTHING""")
    op.execute("""
        INSERT INTO crm_contact_associations (id, contact_id, object_type, object_id, label, created_at)
        SELECT gen_random_uuid(), a.contact_id, 'customer', r.assigned_customer_id, 'primary', now()
          FROM crm_contact_associations a JOIN crm_records r ON a.object_type = 'crm_record' AND a.object_id = r.id
         WHERE r.assigned_customer_id IS NOT NULL
        ON CONFLICT DO NOTHING""")
    op.execute("""UPDATE crm_account_contacts ac SET contact_id = c.id FROM crm_contacts c
                  WHERE ac.contact_id IS NULL AND lower(c.email) = lower(NULLIF(trim(ac.email), ''))""")
    op.execute("""
        INSERT INTO crm_contact_associations (id, contact_id, object_type, object_id, label, created_at)
        SELECT gen_random_uuid(), contact_id, 'customer', customer_id,
               CASE lower(committee_role) WHEN 'decision_maker' THEN 'decision_maker' WHEN 'buyer' THEN 'buyer'
                    WHEN 'influencer' THEN 'influencer' WHEN 'champion' THEN 'champion' WHEN 'user' THEN 'user'
                    WHEN 'blocker' THEN 'blocker' ELSE 'other' END, now()
          FROM crm_account_contacts WHERE contact_id IS NOT NULL
        ON CONFLICT DO NOTHING""")
    # lifecycle from the most advanced linked record (won → customer, opportunity, qualified → sql, else lead)
    op.execute("""
        UPDATE crm_contacts c SET lifecycle_stage = s.stage, lifecycle_changed_at = now() FROM (
            SELECT a.contact_id, (ARRAY['LEAD','SQL','OPPORTUNITY','CUSTOMER'])[max(
                CASE WHEN r.status = 'WON' THEN 4 WHEN r.record_type = 'OPPORTUNITY' THEN 3
                     WHEN r.qualified_flag THEN 2 ELSE 1 END)] AS stage
              FROM crm_contact_associations a JOIN crm_records r ON a.object_type = 'crm_record' AND a.object_id = r.id
             GROUP BY a.contact_id) s
         WHERE c.id = s.contact_id AND c.lifecycle_stage IS NULL""")
    op.execute("""
        INSERT INTO crm_lifecycle_history (id, contact_id, from_stage, to_stage, source, changed_at)
        SELECT gen_random_uuid(), id, NULL, lifecycle_stage, 'migration', now() FROM crm_contacts WHERE lifecycle_stage IS NOT NULL""")

    # T016: teams (from every existing sales_team_id value), tags, required fields per stage, saved views
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_teams (
            id UUID PRIMARY KEY,
            code VARCHAR(100) NOT NULL UNIQUE,
            name VARCHAR(150) NOT NULL,
            parent_id UUID REFERENCES crm_teams(id) ON DELETE SET NULL,
            manager_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
            active_flag BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_team_not_own_parent CHECK (parent_id IS NULL OR parent_id <> id)
        )""")
    op.execute("""
        INSERT INTO crm_teams (id, code, name, created_at, updated_at)
        SELECT gen_random_uuid(), v, v, now(), now() FROM (
            SELECT DISTINCT trim(sales_team_id) AS v FROM crm_records WHERE NULLIF(trim(sales_team_id), '') IS NOT NULL
            UNION SELECT DISTINCT trim(sales_team_id) FROM sales_orders WHERE NULLIF(trim(sales_team_id), '') IS NOT NULL
        ) x
        ON CONFLICT (code) DO NOTHING""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_team_members (
            team_id UUID NOT NULL REFERENCES crm_teams(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role VARCHAR(10) NOT NULL DEFAULT 'member' CHECK (role IN ('member', 'manager')),
            PRIMARY KEY (team_id, user_id)
        )""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_tags (
            id UUID PRIMARY KEY,
            name VARCHAR(60) NOT NULL UNIQUE,
            color VARCHAR(20)
        )""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_record_tags (
            crm_record_id UUID NOT NULL REFERENCES crm_records(id) ON DELETE CASCADE,
            tag_id UUID NOT NULL REFERENCES crm_tags(id) ON DELETE CASCADE,
            PRIMARY KEY (crm_record_id, tag_id)
        )""")
    op.execute("ALTER TABLE crm_pipeline_stages ADD COLUMN IF NOT EXISTS required_fields JSON")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_saved_views (
            id UUID PRIMARY KEY,
            name VARCHAR(120) NOT NULL,
            owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            team_id UUID REFERENCES crm_teams(id) ON DELETE CASCADE,
            view_type VARCHAR(10) NOT NULL DEFAULT 'list' CHECK (view_type IN ('list', 'board', 'calendar')),
            filters JSON NOT NULL DEFAULT '{}',
            columns JSON NOT NULL DEFAULT '[]',
            calendar_field VARCHAR(30),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_crm_saved_views_owner ON crm_saved_views (owner_user_id)")

    # T012: deal score trend
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_deal_score_history (
            id UUID PRIMARY KEY,
            crm_record_id UUID NOT NULL REFERENCES crm_records(id) ON DELETE CASCADE,
            score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
            factors JSON NOT NULL,
            computed_at TIMESTAMPTZ NOT NULL
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_deal_score_history ON crm_deal_score_history (crm_record_id, computed_at)")

    # T013: task queues, repeating tasks, snippets, signatures
    for col, ddl in (("queue", "VARCHAR(60)"), ("recurrence_rule", "VARCHAR(10)"), ("recurrence_every", "INTEGER"),
                     ("recurrence_until", "DATE"), ("recurrence_parent_id", "UUID")):
        op.execute(f"ALTER TABLE crm_activities ADD COLUMN IF NOT EXISTS {col} {ddl}")
    op.execute("CREATE INDEX IF NOT EXISTS ix_crm_activities_queue ON crm_activities (queue) WHERE queue IS NOT NULL")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_crm_activity_recurrence ON crm_activities (recurrence_parent_id, due_datetime) "
               "WHERE recurrence_parent_id IS NOT NULL")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_snippets (
            id UUID PRIMARY KEY,
            name VARCHAR(120) NOT NULL,
            shortcut VARCHAR(30),
            body TEXT NOT NULL,
            owner_user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_email_signatures (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(80) NOT NULL,
            body TEXT NOT NULL,
            is_default BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_signature_default ON crm_email_signatures (user_id) WHERE is_default")

    # T014: routing rules, stage approvals, deal splits, handoffs
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_routing_rules (
            id UUID PRIMARY KEY,
            name VARCHAR(120) NOT NULL,
            priority INTEGER NOT NULL DEFAULT 100,
            active BOOLEAN NOT NULL DEFAULT true,
            conditions JSON NOT NULL DEFAULT '{}',
            method VARCHAR(12) NOT NULL DEFAULT 'ROUND_ROBIN' CHECK (method IN ('ROUND_ROBIN', 'WEIGHTED', 'FIXED')),
            user_ids JSON NOT NULL DEFAULT '[]',
            weights JSON,
            state JSON,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_stage_approval_rules (
            id UUID PRIMARY KEY,
            name VARCHAR(120) NOT NULL,
            stage_id UUID NOT NULL REFERENCES crm_pipeline_stages(id) ON DELETE CASCADE,
            min_expected_revenue NUMERIC(18, 2),
            active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_stage_approval_requests (
            id UUID PRIMARY KEY,
            crm_record_id UUID NOT NULL REFERENCES crm_records(id) ON DELETE CASCADE,
            stage_id UUID NOT NULL REFERENCES crm_pipeline_stages(id) ON DELETE CASCADE,
            rule_id UUID REFERENCES crm_stage_approval_rules(id) ON DELETE SET NULL,
            requested_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            status VARCHAR(10) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
            reason VARCHAR(300),
            decided_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            requested_at TIMESTAMPTZ NOT NULL,
            decided_at TIMESTAMPTZ,
            CONSTRAINT ck_no_self_approval CHECK (decided_by_id IS NULL OR decided_by_id <> requested_by_id)
        )""")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_stage_approval_pending ON crm_stage_approval_requests "
               "(crm_record_id, stage_id) WHERE status = 'PENDING'")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_deal_splits (
            crm_record_id UUID NOT NULL REFERENCES crm_records(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            share_pct NUMERIC(5, 2) NOT NULL CHECK (share_pct > 0 AND share_pct <= 100),
            PRIMARY KEY (crm_record_id, user_id)
        )""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_handoffs (
            id UUID PRIMARY KEY,
            crm_record_id UUID NOT NULL UNIQUE REFERENCES crm_records(id) ON DELETE CASCADE,
            brief JSON NOT NULL,
            status VARCHAR(12) NOT NULL DEFAULT 'OPEN',
            acknowledged_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL
        )""")

    # T017: coaching playlists (clips of consented transcripts)
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_coaching_playlists (
            id UUID PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            description TEXT,
            created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_coaching_clips (
            id UUID PRIMARY KEY,
            playlist_id UUID NOT NULL REFERENCES crm_coaching_playlists(id) ON DELETE CASCADE,
            call_id UUID NOT NULL REFERENCES call_logs(id) ON DELETE CASCADE,
            start_s NUMERIC(10, 2) NOT NULL,
            end_s NUMERIC(10, 2) NOT NULL CHECK (end_s > start_s),
            note VARCHAR(500),
            added_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_coaching_clips_playlist ON crm_coaching_clips (playlist_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_coaching_clips_call ON crm_coaching_clips (call_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS crm_coaching_clips")
    op.execute("DROP TABLE IF EXISTS crm_coaching_playlists")
    op.execute("DROP TABLE IF EXISTS crm_handoffs")
    op.execute("DROP TABLE IF EXISTS crm_deal_splits")
    op.execute("DROP TABLE IF EXISTS crm_stage_approval_requests")
    op.execute("DROP TABLE IF EXISTS crm_stage_approval_rules")
    op.execute("DROP TABLE IF EXISTS crm_routing_rules")
    op.execute("DROP TABLE IF EXISTS crm_email_signatures")
    op.execute("DROP TABLE IF EXISTS crm_snippets")
    op.execute("DROP INDEX IF EXISTS uq_crm_activity_recurrence")
    for col in ("recurrence_parent_id", "recurrence_until", "recurrence_every", "recurrence_rule", "queue"):
        op.execute(f"ALTER TABLE crm_activities DROP COLUMN IF EXISTS {col}")
    op.execute("DROP TABLE IF EXISTS crm_deal_score_history")
    op.execute("DROP TABLE IF EXISTS crm_saved_views")
    op.execute("ALTER TABLE crm_pipeline_stages DROP COLUMN IF EXISTS required_fields")
    op.execute("DROP TABLE IF EXISTS crm_record_tags")
    op.execute("DROP TABLE IF EXISTS crm_tags")
    op.execute("DROP TABLE IF EXISTS crm_team_members")
    op.execute("DROP TABLE IF EXISTS crm_teams")
    op.execute("ALTER TABLE crm_account_contacts DROP COLUMN IF EXISTS contact_id")
    op.execute("DROP TABLE IF EXISTS crm_lifecycle_history")
    op.execute("DROP TABLE IF EXISTS crm_contact_associations")
    op.execute("DROP TABLE IF EXISTS crm_contacts")
    op.execute("ALTER TABLE crm_records DROP COLUMN IF EXISTS pipeline_id")
    op.execute("ALTER TABLE crm_pipeline_stages DROP COLUMN IF EXISTS pipeline_id")
    op.execute("DROP TABLE IF EXISTS crm_pipelines")
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
