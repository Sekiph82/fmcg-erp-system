"""M36.S01.T003 unified conversations inbox: conversation index and per-user read markers."""

from alembic import op

revision = "20261120_0048"
down_revision = "20261119_0047"
branch_labels = None
depends_on = None


def _tables():
    from app.models.crm import CRMConversation, CRMConversationRead

    return CRMConversation.__table__, CRMConversationRead.__table__


def upgrade() -> None:
    for t in _tables():  # fresh databases get them from the model-based baseline
        t.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    for t in reversed(_tables()):
        t.drop(op.get_bind(), checkfirst=True)
