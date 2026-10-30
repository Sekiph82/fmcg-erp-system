"""Track issued RFQ invitations and attributed supplier quotations.

Revision ID: 20261030_0006
Revises: 20261030_0005
Create Date: 2026-10-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20261030_0006"
down_revision = "20261030_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("rfq_responses"):
        raise RuntimeError("Expected the migration-managed rfq_responses table; refusing to create a parallel bid table.")

    status_type = sa.Enum("PENDING", "ISSUED", name="rfqinvitationstatus")
    status_type.create(bind, checkfirst=True)
    existing_columns = {column["name"] for column in inspector.get_columns("rfq_responses")}
    columns = (
        ("invitation_status", status_type, False, "PENDING"),
        ("invitation_issued_at", sa.DateTime(timezone=True), True, None),
        ("invitation_issued_by_id", sa.Uuid(), True, None),
        ("submitted_at", sa.DateTime(timezone=True), True, None),
        ("submitted_by_id", sa.Uuid(), True, None),
    )
    new_column_names = {name for name, *_ in columns}
    overlap = existing_columns.intersection(new_column_names)
    if overlap and overlap != new_column_names:
        raise RuntimeError("rfq_responses has a partial invitation/bid extension; reconcile explicitly before migration.")
    if not overlap:
        for name, column_type, nullable, server_default in columns:
            op.add_column(
                "rfq_responses",
                sa.Column(name, column_type, nullable=nullable, server_default=server_default),
            )
        op.alter_column(
            "rfq_responses",
            "invitation_status",
            server_default=None,
            existing_type=status_type,
            existing_nullable=False,
        )
    else:
        current_columns = {column["name"]: column for column in sa.inspect(bind).get_columns("rfq_responses")}
        if current_columns["invitation_status"]["nullable"]:
            raise RuntimeError("rfq_responses.invitation_status must be NOT NULL; refusing adoption.")
        price_type = current_columns["quoted_unit_price"]["type"]
        if not isinstance(price_type, sa.Numeric) or price_type.precision != 14 or price_type.scale != 4:
            raise RuntimeError("rfq_responses.quoted_unit_price must be NUMERIC(14, 4); refusing adoption.")

    expected_foreign_keys = (
        ("invitation_issued_by_id", "fk_rfq_responses_invitation_issued_by_id_users"),
        ("submitted_by_id", "fk_rfq_responses_submitted_by_id_users"),
    )
    current_foreign_keys = sa.inspect(bind).get_foreign_keys("rfq_responses")
    for column, name in expected_foreign_keys:
        matching = [
            item for item in current_foreign_keys
            if tuple(item.get("constrained_columns") or ()) == (column,)
            and item.get("referred_table") == "users"
            and tuple(item.get("referred_columns") or ()) == ("id",)
        ]
        if any((item.get("options") or {}).get("ondelete", "").upper() == "SET NULL" for item in matching):
            continue
        if any(tuple(item.get("constrained_columns") or ()) == (column,) and item.get("referred_table") != "users" for item in current_foreign_keys):
            raise RuntimeError(f"Unexpected relationship on rfq_responses.{column}; refusing adoption.")
        for item in matching:
            if not item.get("name"):
                raise RuntimeError(f"Cannot safely replace unnamed foreign key on rfq_responses.{column}.")
            op.drop_constraint(item["name"], "rfq_responses", type_="foreignkey")
        op.create_foreign_key(name, "rfq_responses", "users", [column], ["id"], ondelete="SET NULL")

    unique_shapes = {
        tuple(item.get("column_names") or ()) for item in inspector.get_unique_constraints("rfq_responses")
    }
    if ("rfq_id", "supplier_id") not in unique_shapes:
        duplicates = bind.execute(
            sa.text(
                "SELECT 1 FROM rfq_responses GROUP BY rfq_id, supplier_id HAVING count(*) > 1 LIMIT 1"
            )
        ).first()
        if duplicates:
            raise RuntimeError("Duplicate RFQ/supplier responses exist; reconcile explicitly before adding bid uniqueness.")
        op.create_unique_constraint("uq_rfq_response_supplier", "rfq_responses", ["rfq_id", "supplier_id"])

    existing_check_names = {
        item.get("name") for item in sa.inspect(bind).get_check_constraints("rfq_responses")
    }
    for name in ("ck_rfq_response_quoted_price_positive", "ck_rfq_response_lead_time_nonnegative"):
        if name in existing_check_names:
            op.drop_constraint(name, "rfq_responses", type_="check")
    op.create_check_constraint(
        "ck_rfq_response_quoted_price_positive",
        "rfq_responses",
        "quoted_unit_price IS NULL OR (quoted_unit_price > 0 AND quoted_unit_price NOT IN ('NaN', 'Infinity', '-Infinity'))",
    )
    op.create_check_constraint(
        "ck_rfq_response_lead_time_nonnegative",
        "rfq_responses",
        "lead_time_days IS NULL OR lead_time_days >= 0",
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM rfq_responses WHERE invitation_status <> 'PENDING' OR invitation_issued_at IS NOT NULL OR submitted_at IS NOT NULL)"
        )
    ).scalar():
        raise RuntimeError("Cannot downgrade: RFQ invitation or bid attribution data would be destroyed.")
    inspector = sa.inspect(bind)
    check_names = {item.get("name") for item in inspector.get_check_constraints("rfq_responses")}
    for name in ("ck_rfq_response_lead_time_nonnegative", "ck_rfq_response_quoted_price_positive"):
        if name in check_names:
            op.drop_constraint(name, "rfq_responses", type_="check")
    unique_names = {item.get("name") for item in inspector.get_unique_constraints("rfq_responses")}
    if "uq_rfq_response_supplier" in unique_names:
        op.drop_constraint("uq_rfq_response_supplier", "rfq_responses", type_="unique")
    foreign_key_names = {item.get("name") for item in inspector.get_foreign_keys("rfq_responses")}
    for name in (
        "fk_rfq_responses_submitted_by_id_users",
        "fk_rfq_responses_invitation_issued_by_id_users",
    ):
        if name in foreign_key_names:
            op.drop_constraint(name, "rfq_responses", type_="foreignkey")
    op.drop_column("rfq_responses", "submitted_by_id")
    op.drop_column("rfq_responses", "submitted_at")
    op.drop_column("rfq_responses", "invitation_issued_by_id")
    op.drop_column("rfq_responses", "invitation_issued_at")
    op.drop_column("rfq_responses", "invitation_status")
    sa.Enum(name="rfqinvitationstatus").drop(bind, checkfirst=True)
