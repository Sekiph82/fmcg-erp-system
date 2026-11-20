"""M36.S03.T001 sales document engagement: quotation share links and privacy-aware view events."""

from alembic import op

revision = "20261121_0051"
down_revision = "20261121_0050"
branch_labels = None
depends_on = None


def _tables():
    from app.models.crm import CRMDocumentLink, CRMDocumentView

    return CRMDocumentLink.__table__, CRMDocumentView.__table__


def upgrade() -> None:
    for t in _tables():  # fresh databases get them from the model-based baseline
        t.create(op.get_bind(), checkfirst=True)
    op.execute("CREATE INDEX IF NOT EXISTS ix_crm_document_views_link_viewer ON crm_document_views (link_id, viewer_hash, last_seen_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_crm_document_views_link_viewer")
    for t in reversed(_tables()):
        t.drop(op.get_bind(), checkfirst=True)
