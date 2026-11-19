"""M36.S01.T002 sales sequences."""

from alembic import op

revision = "20261119_0042"
down_revision = "20261119_0041"
branch_labels = None
depends_on = None


def _tables():
    from app.models.crm import CRMSequence, CRMSequenceEnrollment, CRMSequenceStep

    return [CRMSequence.__table__, CRMSequenceStep.__table__, CRMSequenceEnrollment.__table__]


def upgrade() -> None:
    for t in _tables():  # fresh databases get them from the model-based baseline
        t.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    for t in reversed(_tables()):
        t.drop(op.get_bind(), checkfirst=True)
