"""M36.S04.T005 knowledge-base article feedback."""

from alembic import op

revision = "20261112_0040"
down_revision = "20261112_0039"
branch_labels = None
depends_on = None


def _table():
    from app.models.knowledge_base import KBArticleFeedback

    return KBArticleFeedback.__table__


def upgrade() -> None:
    _table().create(op.get_bind(), checkfirst=True)  # fresh databases get it from the model-based baseline


def downgrade() -> None:
    _table().drop(op.get_bind(), checkfirst=True)
