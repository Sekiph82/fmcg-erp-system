"""M36.S04.T003 customer quote acceptance with signed, tamper-evident decision record."""

from alembic import op

revision = "20261121_0052"
down_revision = "20261121_0051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.models.crm import CRMQuoteDecision  # fresh databases get it from the model-based baseline

    CRMQuoteDecision.__table__.create(op.get_bind(), checkfirst=True)
    op.execute("ALTER TABLE crm_quote_decisions ADD COLUMN IF NOT EXISTS document_snapshot JSON")


def downgrade() -> None:
    # M48.S01.T023 (audit F3): evidence is archived (renamed), never dropped; see app.db.downgrade_archive.
    from app.db.downgrade_archive import archive_tables

    archive_tables(op.get_bind(), ['crm_quote_decisions'], "0052")
