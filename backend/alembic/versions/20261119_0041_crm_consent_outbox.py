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
    # M48.S01.T023 (audit F3): evidence is archived (renamed), never dropped; see app.db.downgrade_archive.
    from app.db.downgrade_archive import archive_tables

    archive_tables(op.get_bind(), ['crm_outbound_messages', 'crm_contact_consents'], "0041")
