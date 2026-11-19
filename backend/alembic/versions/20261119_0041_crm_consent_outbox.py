"""M36 consent register and outbound e-mail outbox."""

from alembic import op

revision = "20261119_0041"
down_revision = "20261112_0040"
branch_labels = None
depends_on = None


def _tables():
    from app.models.crm import CRMContactConsent, CRMOutboundMessage

    return [CRMContactConsent.__table__, CRMOutboundMessage.__table__]


def upgrade() -> None:
    for t in _tables():  # fresh databases get them from the model-based baseline
        t.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    for t in reversed(_tables()):
        t.drop(op.get_bind(), checkfirst=True)
