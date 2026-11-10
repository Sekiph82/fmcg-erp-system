"""M35: supplier audit lifecycle - supplier-scoped audits and audited approval decisions."""

from alembic import op
import sqlalchemy as sa

revision = "20261110_0029"
down_revision = "20261110_0028"
branch_labels = None
depends_on = None

UUID = sa.Uuid(as_uuid=True)


def upgrade() -> None:
    op.add_column("qms_audit_checklists", sa.Column(
        "supplier_id", UUID, sa.ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_qms_audit_checklists_supplier_id", "qms_audit_checklists", ["supplier_id"])
    op.add_column("qms_supplier_food_safety", sa.Column(
        "audit_checklist_id", UUID, sa.ForeignKey("qms_audit_checklists.id", ondelete="SET NULL"), nullable=True))
    op.add_column("qms_supplier_food_safety", sa.Column(
        "decided_by_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    op.add_column("qms_supplier_food_safety", sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("qms_supplier_food_safety", sa.Column("decision_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    for column in ("decision_notes", "decided_at", "decided_by_id", "audit_checklist_id"):
        op.drop_column("qms_supplier_food_safety", column)
    op.drop_index("ix_qms_audit_checklists_supplier_id", table_name="qms_audit_checklists")
    op.drop_column("qms_audit_checklists", "supplier_id")
