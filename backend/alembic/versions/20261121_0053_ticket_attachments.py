"""M36.S04.T004 helpdesk ticket attachments (customer portal and staff, scanned, shared on approval)."""

from alembic import op

revision = "20261121_0053"
down_revision = "20261121_0052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.models.helpdesk import TicketAttachment  # fresh databases get it from the model-based baseline

    TicketAttachment.__table__.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ticket_attachments")
