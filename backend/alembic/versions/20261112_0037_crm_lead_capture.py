"""M36.S02.T001 website lead capture: forms and submissions."""

from alembic import op

revision = "20261112_0037"
down_revision = "20261112_0036"
branch_labels = None
depends_on = None


def _tables():
    from app.models.crm import CRMLeadForm, CRMLeadSubmission

    return [CRMLeadForm.__table__, CRMLeadSubmission.__table__]


def upgrade() -> None:
    for table in _tables():  # fresh databases already have them from the model-based baseline
        table.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    for table in reversed(_tables()):
        table.drop(op.get_bind(), checkfirst=True)
