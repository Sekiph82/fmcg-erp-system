"""Add a monotonic allocator for MPS production-order numbers."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20261019_0010"
down_revision = "20260602_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("CREATE SEQUENCE IF NOT EXISTS mps_po_number_seq"))
    op.execute(
        sa.text(
            """
            SELECT setval(
                'mps_po_number_seq',
                GREATEST(
                    COALESCE(
                        (
                            SELECT MAX(CAST(SUBSTRING(order_no FROM 8) AS BIGINT))
                            FROM production_orders
                            WHERE order_no ~ '^PO-MPS-[0-9]+$'
                        ),
                        1
                    ),
                    1
                ),
                COALESCE(
                    (
                        SELECT MAX(CAST(SUBSTRING(order_no FROM 8) AS BIGINT))
                        FROM production_orders
                        WHERE order_no ~ '^PO-MPS-[0-9]+$'
                    ),
                    0
                ) > 0
            )
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP SEQUENCE IF EXISTS mps_po_number_seq"))
