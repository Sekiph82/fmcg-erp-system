"""M42: employee digital business cards; every current employee gets a card (published unless terminated/archived)."""

import re
import unicodedata
import uuid

import sqlalchemy as sa
from alembic import op

revision = "20261124_0071"
down_revision = "20261121_0070"
branch_labels = None
depends_on = None

_TR = str.maketrans({"ı": "i", "İ": "I", "ş": "s", "Ş": "S", "ğ": "g", "Ğ": "G", "ç": "c", "Ç": "C",
                     "ö": "o", "Ö": "O", "ü": "u", "Ü": "U"})


def _slug(name: str) -> str:   # same rule as app.services.business_card_service.slugify (kept here: migrations stay frozen)
    ascii_name = unicodedata.normalize("NFKD", (name or "").translate(_TR)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")[:100].strip("-") or "employee"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS employee_business_cards (
            id UUID PRIMARY KEY,
            employee_id UUID NOT NULL UNIQUE REFERENCES hr_employees(id) ON DELETE CASCADE,
            slug VARCHAR(120) NOT NULL UNIQUE,
            status VARCHAR(12) NOT NULL DEFAULT 'PUBLISHED',
            show_phone BOOLEAN NOT NULL DEFAULT true,
            show_whatsapp BOOLEAN NOT NULL DEFAULT true,
            show_email BOOLEAN NOT NULL DEFAULT true,
            title_en VARCHAR(150),
            photo TEXT,
            photo_consent_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            photo_consent_at TIMESTAMPTZ,
            published_at TIMESTAMPTZ,
            revoked_at TIMESTAMPTZ,
            revoked_reason VARCHAR(200),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_employee_business_cards_status CHECK (status IN ('PUBLISHED', 'REVOKED'))
        )""")
    conn = op.get_bind()
    taken = set(conn.execute(sa.text("SELECT slug FROM employee_business_cards")).scalars())
    rows = conn.execute(sa.text("""
        SELECT e.id, e.full_name, e.status::text AS status, e.archived_at FROM hr_employees e
         WHERE NOT EXISTS (SELECT 1 FROM employee_business_cards c WHERE c.employee_id = e.id)
         ORDER BY e.hire_date, e.created_at, e.id""")).all()
    for emp_id, name, status, archived in rows:
        base, n = _slug(name), 2
        slug = base
        while slug in taken:
            slug, n = f"{base}-{n}", n + 1
        taken.add(slug)
        live = status != "TERMINATED" and archived is None
        conn.execute(sa.text("""
            INSERT INTO employee_business_cards (id, employee_id, slug, status, published_at, revoked_at, revoked_reason)
            VALUES (:id, :emp, :slug, :status, CASE WHEN :live THEN now() END, CASE WHEN :live THEN NULL ELSE now() END,
                    CASE WHEN :live THEN NULL ELSE 'employee closed' END)"""),
            {"id": uuid.uuid4(), "emp": emp_id, "slug": slug, "status": "PUBLISHED" if live else "REVOKED", "live": live})


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS employee_business_cards")
