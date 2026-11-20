"""M36.S01.T001 two-way e-mail: IMAP/SMTP mailbox settings, attachment metadata and reply headers."""

import sqlalchemy as sa
from alembic import op

revision = "20261121_0049"
down_revision = "20261120_0048"
branch_labels = None
depends_on = None

_ACCOUNT = [
    ("imap_host", sa.String(255)), ("imap_port", sa.Integer()), ("smtp_host", sa.String(255)),
    ("smtp_port", sa.Integer()), ("username", sa.String(255)), ("secret_enc", sa.Text()),
    ("imap_uidvalidity", sa.BigInteger()), ("imap_last_uid", sa.BigInteger()),
]
_MESSAGE = [("attachments", sa.JSON()), ("in_reply_to", sa.String(500))]


def _add(table, cols):
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}
    for name, type_ in cols:
        if name not in existing:  # fresh databases already have them from the model-based baseline
            op.add_column(table, sa.Column(name, type_, nullable=True))


def upgrade() -> None:
    _add("email_accounts", _ACCOUNT)
    _add("email_messages", _MESSAGE)
    op.execute("CREATE INDEX IF NOT EXISTS ix_email_messages_external_message_id ON email_messages (external_message_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_email_messages_external_message_id")
    for name, _ in _MESSAGE:
        op.drop_column("email_messages", name)
    for name, _ in _ACCOUNT:
        op.drop_column("email_accounts", name)
