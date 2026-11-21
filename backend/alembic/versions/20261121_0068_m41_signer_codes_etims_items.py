"""M41: one-time e-mail codes for quote signers (S01.T002) and KRA eTIMS item codes on products (S01.T003)."""

from alembic import op

revision = "20261121_0068"
down_revision = "20261121_0067"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS crm_quote_signer_codes (
            id UUID PRIMARY KEY,
            link_id UUID NOT NULL REFERENCES crm_document_links(id) ON DELETE CASCADE,
            email VARCHAR(254) NOT NULL,
            code_hash VARCHAR(64) NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            expires_at TIMESTAMPTZ NOT NULL,
            used_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_crm_quote_signer_codes_link ON crm_quote_signer_codes (link_id, created_at)")
    op.execute("ALTER TABLE crm_quote_decisions ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS etims_item_code VARCHAR(30)")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS etims_item_class_code VARCHAR(20)")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS etims_tax_type VARCHAR(2)")


def downgrade() -> None:
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS etims_tax_type")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS etims_item_class_code")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS etims_item_code")
    op.execute("ALTER TABLE crm_quote_decisions DROP COLUMN IF EXISTS email_verified_at")
    op.execute("DROP TABLE IF EXISTS crm_quote_signer_codes")
