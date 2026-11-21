"""M36.S05.T005 account-based marketing: target-account groups, members, buying-committee contacts."""

from alembic import op

revision = "20261121_0062"
down_revision = "20261121_0061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_account_groups (
            id UUID PRIMARY KEY,
            name VARCHAR(150) NOT NULL UNIQUE,
            description TEXT,
            owner_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            campaign_started_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_account_group_members (
            group_id UUID NOT NULL REFERENCES crm_account_groups(id) ON DELETE CASCADE,
            customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
            tier INTEGER NOT NULL DEFAULT 2 CHECK (tier BETWEEN 1 AND 3),
            added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (group_id, customer_id)
        )""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_account_contacts (
            id UUID PRIMARY KEY,
            customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
            full_name VARCHAR(150) NOT NULL,
            title VARCHAR(150),
            email VARCHAR(254),
            phone VARCHAR(50),
            committee_role VARCHAR(20) NOT NULL DEFAULT 'INFLUENCER'
                CHECK (committee_role IN ('DECISION_MAKER','BUYER','INFLUENCER','CHAMPION','USER','BLOCKER')),
            notes VARCHAR(500),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_crm_account_contacts_customer_id ON crm_account_contacts (customer_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_crm_account_contacts_customer_email ON crm_account_contacts (customer_id, lower(email)) WHERE email IS NOT NULL")


def downgrade() -> None:
    for t in ("crm_account_contacts", "crm_account_group_members", "crm_account_groups"):
        op.execute(f"DROP TABLE IF EXISTS {t}")
