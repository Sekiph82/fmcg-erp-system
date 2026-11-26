"""M48 critical software completion: ad mutation ledger/tree, social publish states, card payments, e-signature
providers, warehouse run mode.

Tables are created from their ORM definitions (checkfirst), like 0075–0077; column additions are explicit SQL.
Downgrade drops them: ad mutation history, card payment records and provider envelopes are lost.
"""

from alembic import op

revision = "20261128_0078"
down_revision = "20261127_0077"
branch_labels = None
depends_on = None

# Parents first (downgrade drops in reverse).
TABLES = [
    "ads_account_controls", "ads_campaign_nodes", "ads_approvals", "ads_mutations",        # T001–T004
    "card_provider_configs", "card_payments", "card_refunds",                              # T010
    "esign_provider_configs", "esign_envelopes", "esign_webhook_events",                   # T009
]

COLUMNS = [
    ("social_posts", "provider_ref", "VARCHAR(120)"),                                       # T005 publish state machine
    ("social_posts", "provider_status", "VARCHAR(40)"),
    ("social_posts", "fail_reason", "VARCHAR(120)"),
    ("social_posts", "publish_mode", "VARCHAR(9)"),
    ("social_posts", "publish_options", "JSON"),
    ("social_posts", "claimed_at", "TIMESTAMPTZ"),
    ("social_posts", "submitted_at", "TIMESTAMPTZ"),
    ("social_posts", "next_poll_at", "TIMESTAMPTZ"),
    ("social_posts", "poll_count", "INTEGER NOT NULL DEFAULT 0"),
    ("dw_runs", "mode", "VARCHAR(10)"),                                                     # T007/T008 SIMULATED | LIVE
    ("stock_movements", "idempotency_key", "VARCHAR(64) UNIQUE"),                           # T018 transfer replay
]

INDEXES = [
    ("ix_social_posts_provider_ref", "social_posts", "provider_ref"),
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
