"""Network label printers and print-job dispatch tracking."""

from alembic import op
import sqlalchemy as sa

revision = "20261111_0032"
down_revision = "20261111_0031"
branch_labels = None
depends_on = None

UUID = sa.Uuid(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "label_printers",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("protocol", sa.String(10), nullable=False, server_default="ZPL"),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False, server_default="9100"),
        sa.Column("dpi", sa.Integer(), nullable=False, server_default="203"),
        sa.Column("label_width_mm", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("label_height_mm", sa.Integer(), nullable=False, server_default="150"),
        sa.Column("location", sa.String(200)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("protocol IN ('ZPL', 'TSPL')", name="ck_label_printers_protocol"),
        sa.CheckConstraint("port BETWEEN 1 AND 65535", name="ck_label_printers_port"),
        sa.CheckConstraint("dpi IN (203, 300, 600)", name="ck_label_printers_dpi"),
    )
    op.add_column("gs1_label_print_jobs", sa.Column(
        "printer_id", UUID, sa.ForeignKey("label_printers.id", ondelete="SET NULL"), nullable=True))
    op.add_column("gs1_label_print_jobs", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("gs1_label_print_jobs", "error_message")
    op.drop_column("gs1_label_print_jobs", "printer_id")
    op.drop_table("label_printers")
