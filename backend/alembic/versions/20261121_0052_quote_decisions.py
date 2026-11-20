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
    op.execute("DROP TABLE IF EXISTS crm_quote_decisions")
