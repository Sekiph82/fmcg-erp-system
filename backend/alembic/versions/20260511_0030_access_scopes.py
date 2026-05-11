"""erp-wide access scopes

Revision ID: 20260511_0030
Revises: 20260511_0020
Create Date: 2026-05-11 13:20:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260511_0030"
down_revision = "20260511_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "permissions",
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "roles",
        sa.Column("is_system_role", sa.Boolean(), server_default=sa.false(), nullable=False),
    )

    op.create_table(
        "access_scopes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scope_type", sa.String(length=80), nullable=False),
        sa.Column("scope_id", sa.String(length=120), nullable=False),
        sa.Column("scope_name", sa.String(length=255), nullable=True),
        sa.Column("can_view", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("can_create", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("can_edit", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("can_delete", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("can_approve", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("can_post", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("can_release", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("can_cancel", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("can_export", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("can_import", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("can_transfer", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("can_adjust", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("can_receive", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("can_dispatch", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "(user_id IS NOT NULL AND role_id IS NULL) OR (user_id IS NULL AND role_id IS NOT NULL)",
            name="ck_access_scopes_exactly_one_owner",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_access_scopes_user_id", "access_scopes", ["user_id"])
    op.create_index("ix_access_scopes_role_id", "access_scopes", ["role_id"])
    op.create_index("ix_access_scopes_scope", "access_scopes", ["scope_type", "scope_id"])
    op.create_index("ix_access_scopes_user_scope_type", "access_scopes", ["user_id", "scope_type"])
    op.create_index("ix_access_scopes_role_scope_type", "access_scopes", ["role_id", "scope_type"])
    op.create_index(
        "uq_access_scopes_user_scope",
        "access_scopes",
        ["user_id", "scope_type", "scope_id"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.create_index(
        "uq_access_scopes_role_scope",
        "access_scopes",
        ["role_id", "scope_type", "scope_id"],
        unique=True,
        postgresql_where=sa.text("role_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_access_scopes_role_scope", table_name="access_scopes")
    op.drop_index("uq_access_scopes_user_scope", table_name="access_scopes")
    op.drop_index("ix_access_scopes_role_scope_type", table_name="access_scopes")
    op.drop_index("ix_access_scopes_user_scope_type", table_name="access_scopes")
    op.drop_index("ix_access_scopes_scope", table_name="access_scopes")
    op.drop_index("ix_access_scopes_role_id", table_name="access_scopes")
    op.drop_index("ix_access_scopes_user_id", table_name="access_scopes")
    op.drop_table("access_scopes")
    op.drop_column("roles", "is_system_role")
    op.drop_column("permissions", "is_active")
