"""M41 review: who last set a discount (may not approve it), and open drafts created before the discount approval
existed are checked once against the limit (SystemConfig sales.discount_approval_limit_pct, default 10 %)."""

from alembic import op

revision = "20261121_0070"
down_revision = "20261121_0069"
branch_labels = None
depends_on = None

LIMIT = """COALESCE((SELECT NULLIF(trim(value), '')::numeric FROM system_configs
                     WHERE key = 'sales.discount_approval_limit_pct' AND trim(value) ~ '^[0-9]+(\\.[0-9]+)?$'), 10)"""


def upgrade() -> None:
    for table in ("quotations", "sales_orders"):
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS discount_changed_by_id UUID "
                   "REFERENCES users(id) ON DELETE SET NULL")
    # quotations: percentages; highest line discount or whole-document discount (lines and header)
    op.execute(f"""
        UPDATE quotations q SET discount_approval_required = true, approval_status = 'PENDING_DISCOUNT',
               discount_approved_by_id = NULL, discount_approved_at = NULL, discount_changed_by_id = q.created_by_id
          FROM (SELECT quote_id, MAX(discount_pct) AS line_max, SUM(qty * unit_price) AS gross,
                       SUM(qty * unit_price * (1 - discount_pct / 100)) AS net
                  FROM quotation_lines GROUP BY quote_id) s
         WHERE s.quote_id = q.id AND q.status = 'DRAFT' AND q.approval_status IS NULL
           AND (s.line_max > {LIMIT}
                OR (s.gross > 0 AND (1 - s.net * (1 - q.discount_pct / 100) / s.gross) * 100 > {LIMIT}))""")
    # sales orders: fractions
    op.execute(f"""
        UPDATE sales_orders o SET discount_approval_required = true, approval_status = 'PENDING_DISCOUNT',
               discount_approved_by_id = NULL, discount_approved_at = NULL, discount_changed_by_id = o.created_by_id
          FROM (SELECT so_id, MAX(discount_pct) AS line_max, SUM(ordered_quantity * unit_price) AS gross,
                       SUM(ordered_quantity * unit_price * (1 - discount_pct)) AS net
                  FROM so_lines GROUP BY so_id) s
         WHERE s.so_id = o.id AND o.status = 'DRAFT' AND o.approval_status IS NULL
           AND (s.line_max * 100 > {LIMIT} OR (s.gross > 0 AND (1 - s.net / s.gross) * 100 > {LIMIT}))""")


def downgrade() -> None:
    for table in ("quotations", "sales_orders"):
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS discount_changed_by_id")
