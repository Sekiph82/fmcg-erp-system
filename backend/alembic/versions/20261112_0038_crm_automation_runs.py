"""M36.S01.T004 CRM automation run log (idempotent per rule + event)."""

from alembic import op

revision = "20261112_0038"
down_revision = "20261112_0037"
branch_labels = None
depends_on = None


def _table():
    from app.models.crm import CRMAutomationRun

    return CRMAutomationRun.__table__


def upgrade() -> None:
    _table().create(op.get_bind(), checkfirst=True)  # fresh databases get it from the model-based baseline


def downgrade() -> None:
    _table().drop(op.get_bind(), checkfirst=True)
