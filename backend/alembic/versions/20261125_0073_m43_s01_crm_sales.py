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


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS booking_page_bookings")
    op.execute("DROP TABLE IF EXISTS booking_pages")
    op.execute("DROP TABLE IF EXISTS calendar_busy_blocks")
    op.execute("DROP TABLE IF EXISTS calendar_event_links")
    op.execute("DROP INDEX IF EXISTS uq_email_accounts_oauth")
    op.execute("ALTER TABLE email_accounts DROP COLUMN IF EXISTS oauth_connection_id")
