"""M36.S03.T005 website live chat: sessions (visitor token as digest) and messages."""

from alembic import op

revision = "20261121_0055"
down_revision = "20261121_0054"
branch_labels = None
depends_on = None


def _tables():
    from app.models.crm import CRMChatMessage, CRMChatSession

    return CRMChatSession.__table__, CRMChatMessage.__table__


def upgrade() -> None:
    for t in _tables():  # fresh databases get them from the model-based baseline
        t.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    # M48.S01.T023 (audit F3): evidence is archived (renamed), never dropped; see app.db.downgrade_archive.
    from app.db.downgrade_archive import archive_tables

    archive_tables(op.get_bind(), ['crm_chat_messages', 'crm_chat_sessions'], "0055")
