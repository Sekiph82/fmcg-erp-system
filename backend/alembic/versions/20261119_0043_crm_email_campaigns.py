"""M36.S02.T005 segment e-mail campaigns."""

from alembic import op

revision = "20261119_0043"
down_revision = "20261119_0042"
branch_labels = None
depends_on = None


def _table():
    from app.models.crm import CRMEmailCampaign

    return CRMEmailCampaign.__table__


def upgrade() -> None:
    _table().create(op.get_bind(), checkfirst=True)  # fresh databases get it from the model-based baseline


def downgrade() -> None:
    _table().drop(op.get_bind(), checkfirst=True)
