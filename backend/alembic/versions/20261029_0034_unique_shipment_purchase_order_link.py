"""make purchase-order links unique within an international shipment

Revision ID: 20261029_0034
Revises: 20261029_0033
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa


revision = "20261029_0034"
down_revision = "20261029_0033"
branch_labels = None
depends_on = None


CONSTRAINT_NAME = "uq_shipment_po_links_shipment_po"
MIGRATION_MARKER = "added by Alembic revision 20261029_0034"


def upgrade() -> None:
    bind = op.get_bind()
    duplicates = op.get_bind().execute(
        sa.text(
            """
            SELECT shipment_id, po_id
            FROM shipment_po_links
            GROUP BY shipment_id, po_id
            HAVING count(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicates:
        raise RuntimeError(
            "Cannot add shipment purchase-order uniqueness while duplicate links exist; "
            "review shipment_po_links before retrying migration."
        )
    constraint_exists = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM pg_constraint
            WHERE conrelid = 'shipment_po_links'::regclass
              AND conname = :constraint_name
            """
        ),
        {"constraint_name": CONSTRAINT_NAME},
    ).first()
    if not constraint_exists:
        op.create_unique_constraint(
            CONSTRAINT_NAME,
            "shipment_po_links",
            ["shipment_id", "po_id"],
        )
        op.execute(
            f"COMMENT ON CONSTRAINT {CONSTRAINT_NAME} ON shipment_po_links "
            f"IS '{MIGRATION_MARKER}'"
        )


def downgrade() -> None:
    bind = op.get_bind()
    marker = bind.execute(
        sa.text(
            """
            SELECT obj_description(oid, 'pg_constraint')
            FROM pg_constraint
            WHERE conrelid = 'shipment_po_links'::regclass
              AND conname = :constraint_name
            """
        ),
        {"constraint_name": CONSTRAINT_NAME},
    ).scalar_one_or_none()
    # Fresh databases may already receive this constraint from the squashed
    # baseline's current ORM metadata. Remove it only when this revision added it.
    if marker == MIGRATION_MARKER:
        op.drop_constraint(CONSTRAINT_NAME, "shipment_po_links", type_="unique")
