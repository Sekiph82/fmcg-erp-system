"""M41 review: quotation totals counted tax twice (line_total already includes tax). Recompute stored totals for quotes
that are still open (DRAFT, or SENT without a customer decision). Answered/accepted/converted quotes keep their numbers:
the signed content and its evidence hash must not change."""

from alembic import op

revision = "20261121_0069"
down_revision = "20261121_0068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE quotations q
           SET total_amount = round(s.net * (1 - q.discount_pct / 100), 4),
               tax_amount   = round(s.tax * (1 - q.discount_pct / 100), 4),
               grand_total  = round(s.net * (1 - q.discount_pct / 100), 4) + round(s.tax * (1 - q.discount_pct / 100), 4)
          FROM (SELECT quote_id,
                       SUM(qty * unit_price * (1 - discount_pct / 100)) AS net,
                       SUM(qty * unit_price * (1 - discount_pct / 100) * tax_rate / 100) AS tax
                  FROM quotation_lines GROUP BY quote_id) s
         WHERE s.quote_id = q.id
           AND q.status IN ('DRAFT', 'SENT')
           AND NOT EXISTS (SELECT 1 FROM crm_quote_decisions d WHERE d.quotation_id = q.id)""")


def downgrade() -> None:
    pass  # the old totals were wrong; nothing to restore
