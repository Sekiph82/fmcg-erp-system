"""Per-employee registered e-signatures (recorded by IT, visible only to their owner)."""

from alembic import op

revision = "20261119_0044"
down_revision = "20261119_0043"
branch_labels = None
depends_on = None


def _table():
    from app.models.esign import UserSignatureProfile

    return UserSignatureProfile.__table__


def upgrade() -> None:
    _table().create(op.get_bind(), checkfirst=True)  # fresh databases get it from the model-based baseline


def downgrade() -> None:
    _table().drop(op.get_bind(), checkfirst=True)
