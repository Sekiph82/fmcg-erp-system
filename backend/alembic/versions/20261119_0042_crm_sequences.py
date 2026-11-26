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
    # M48.S01.T023 (audit F3): evidence is archived (renamed), never dropped; see app.db.downgrade_archive.
    from app.db.downgrade_archive import archive_tables

    archive_tables(op.get_bind(), ['crm_sequence_enrollments', 'crm_sequence_steps', 'crm_sequences'], "0042")
