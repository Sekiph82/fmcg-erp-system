"""plugin_marketplace_gap70

Revision ID: f1a2b3c4e5d6
Revises: f0a1b2c3d4e5
Create Date: 2026-05-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "f1a2b3c4e5d6"
down_revision = "f0a1b2c3d4e5"
branch_labels = None
depends_on = None


INSTALL_STATUSES = ["INSTALLED", "DISABLED", "UPDATE_AVAILABLE", "UNINSTALLED", "ERROR"]
LIFECYCLE_ACTIONS = ["INSTALL", "ENABLE", "DISABLE", "UNINSTALL", "UPDATE", "CONFIGURE", "TEST"]


def upgrade() -> None:
    install_status_enum = postgresql.ENUM(*INSTALL_STATUSES, name="plugininstallstatus")
    lifecycle_action_enum = postgresql.ENUM(*LIFECYCLE_ACTIONS, name="pluginlifecycleaction")
    install_status_enum.create(op.get_bind(), checkfirst=True)
    lifecycle_action_enum.create(op.get_bind(), checkfirst=True)

    op.add_column("integration_connector_registry", sa.Column("current_version", sa.String(40), nullable=False, server_default="1.0.0"))
    op.add_column("integration_connector_registry", sa.Column("module_key", sa.String(100), nullable=True))
    op.add_column("integration_connector_registry", sa.Column("dependency_codes", sa.Text(), nullable=True))
    op.add_column("integration_connector_registry", sa.Column("required_permissions", sa.Text(), nullable=True))
    op.add_column("integration_connector_registry", sa.Column("supports_tenant_config", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("integration_connector_registry", sa.Column("is_core", sa.Boolean(), nullable=False, server_default="false"))
    op.create_index("ix_integration_connector_registry_module_key", "integration_connector_registry", ["module_key"])

    op.create_table(
        "integration_plugin_installations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("integration_connector_registry.connector_id", ondelete="SET NULL"), nullable=True),
        sa.Column("connector_code", sa.String(100), nullable=False),
        sa.Column("tenant_key", sa.String(100), nullable=False, server_default="default"),
        sa.Column("installed_version", sa.String(40), nullable=False, server_default="1.0.0"),
        sa.Column("status", sa.Enum(*INSTALL_STATUSES, name="plugininstallstatus"), nullable=False),
        sa.Column("environment", sa.String(20), nullable=False, server_default="sandbox"),
        sa.Column("config_json", sa.Text(), nullable=True),
        sa.Column("installed_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("connector_code", "tenant_key", name="uq_plugin_install_connector_tenant"),
    )
    op.create_index("ix_integration_plugin_installations_connector_id", "integration_plugin_installations", ["connector_id"])
    op.create_index("ix_integration_plugin_installations_connector_code", "integration_plugin_installations", ["connector_code"])
    op.create_index("ix_integration_plugin_installations_tenant_key", "integration_plugin_installations", ["tenant_key"])
    op.create_index("ix_integration_plugin_installations_status", "integration_plugin_installations", ["status"])

    op.create_table(
        "integration_plugin_lifecycle_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("installation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("integration_plugin_installations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("connector_code", sa.String(100), nullable=False),
        sa.Column("tenant_key", sa.String(100), nullable=False, server_default="default"),
        sa.Column("action", sa.Enum(*LIFECYCLE_ACTIONS, name="pluginlifecycleaction"), nullable=False),
        sa.Column("previous_status", sa.String(40), nullable=True),
        sa.Column("new_status", sa.String(40), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_integration_plugin_lifecycle_events_installation_id", "integration_plugin_lifecycle_events", ["installation_id"])
    op.create_index("ix_integration_plugin_lifecycle_events_connector_code", "integration_plugin_lifecycle_events", ["connector_code"])
    op.create_index("ix_integration_plugin_lifecycle_events_tenant_key", "integration_plugin_lifecycle_events", ["tenant_key"])


def downgrade() -> None:
    op.drop_index("ix_integration_plugin_lifecycle_events_tenant_key", table_name="integration_plugin_lifecycle_events")
    op.drop_index("ix_integration_plugin_lifecycle_events_connector_code", table_name="integration_plugin_lifecycle_events")
    op.drop_index("ix_integration_plugin_lifecycle_events_installation_id", table_name="integration_plugin_lifecycle_events")
    op.drop_table("integration_plugin_lifecycle_events")
    op.drop_index("ix_integration_plugin_installations_status", table_name="integration_plugin_installations")
    op.drop_index("ix_integration_plugin_installations_tenant_key", table_name="integration_plugin_installations")
    op.drop_index("ix_integration_plugin_installations_connector_code", table_name="integration_plugin_installations")
    op.drop_index("ix_integration_plugin_installations_connector_id", table_name="integration_plugin_installations")
    op.drop_table("integration_plugin_installations")
    op.drop_index("ix_integration_connector_registry_module_key", table_name="integration_connector_registry")
    op.drop_column("integration_connector_registry", "is_core")
    op.drop_column("integration_connector_registry", "supports_tenant_config")
    op.drop_column("integration_connector_registry", "required_permissions")
    op.drop_column("integration_connector_registry", "dependency_codes")
    op.drop_column("integration_connector_registry", "module_key")
    op.drop_column("integration_connector_registry", "current_version")
    op.execute("DROP TYPE IF EXISTS pluginlifecycleaction")
    op.execute("DROP TYPE IF EXISTS plugininstallstatus")
