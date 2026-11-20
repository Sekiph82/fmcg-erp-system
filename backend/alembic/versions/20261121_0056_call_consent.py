"""M36.S04.T002 telephony: recording consent, retention date and transcript on call logs."""

from alembic import op

revision = "20261121_0056"
down_revision = "20261121_0055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS recording_consent BOOLEAN NOT NULL DEFAULT FALSE")
    op.execute("ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS consent_note VARCHAR(300)")
    op.execute("ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS recording_expires_at TIMESTAMPTZ")
    op.execute("ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS transcript TEXT")
    # older recordings have no consent on file: the API hides their links (data kept, nothing deleted here)


def downgrade() -> None:
    for col in ("transcript", "recording_expires_at", "consent_note", "recording_consent"):
        op.execute(f"ALTER TABLE call_logs DROP COLUMN IF EXISTS {col}")
