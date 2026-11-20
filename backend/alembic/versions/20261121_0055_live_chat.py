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
    for t in reversed(_tables()):
        t.drop(op.get_bind(), checkfirst=True)
