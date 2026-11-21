"""M40.S01.T004 merchandiser shelf checks per visit."""

from alembic import op

revision = "20261121_0059"
down_revision = "20261121_0058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS field_shelf_checks (
            id UUID PRIMARY KEY,
            visit_id UUID NOT NULL REFERENCES visit_logs(id) ON DELETE CASCADE,
            product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            facings INTEGER NOT NULL DEFAULT 0 CHECK (facings >= 0),
            out_of_stock BOOLEAN NOT NULL DEFAULT FALSE,
            shelf_price NUMERIC(14, 2) CHECK (shelf_price IS NULL OR shelf_price >= 0),
            planogram_ok BOOLEAN,
            notes VARCHAR(300),
            photo_key VARCHAR(64),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_field_shelf_checks_visit_product UNIQUE (visit_id, product_id)
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_field_shelf_checks_visit_id ON field_shelf_checks (visit_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_field_shelf_checks_product_id ON field_shelf_checks (product_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS field_shelf_checks")
